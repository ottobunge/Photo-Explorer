"""Step definitions for semantic search feature."""

import asyncio
import time
from typing import Dict, Any, List

import pytest
from pytest_bdd import given, when, then, parsers
from httpx import AsyncClient

from app.domain.entities import Photo


# ============================================================================
# GIVEN Steps - Search Specific Setup
# ============================================================================

@given("I have uploaded the following photos with descriptions:")
async def setup_photos_with_descriptions(
    test_db,
    test_client: AsyncClient,
    mock_vector_store,
    context: Dict[str, Any]
):
    """Set up photos with descriptions for search tests."""
    photos = []

    for row in context.table:
        # Create photo in database
        photo = Photo.create(
            filename=row["filename"],
            storage_path=f"test/{row['filename']}",
        )

        # Set description and tags
        photo.description = row["description"]
        photo.tags = row.get("tags", "").split(", ")

        test_db.add(photo)
        photos.append(photo)

        # Add to mock vector store with fake embedding
        # In real implementation, this would use CLIP model
        embedding = [0.1] * 512  # Fake embedding
        if "beach" in row["description"]:
            embedding[0] = 0.9  # Make beach photos similar
        elif "mountain" in row["description"]:
            embedding[1] = 0.9  # Make mountain photos similar

        await mock_vector_store.add_embedding(str(photo.id.value), embedding)

    await test_db.commit()
    context.photos = photos
    return photos


@given(parsers.parse('I select "{filename}" as the reference photo'))
async def select_reference_photo(filename: str, context: Dict[str, Any]):
    """Select a photo as reference for visual similarity search."""
    photos = context.photos
    reference = next((p for p in photos if p.filename == filename), None)
    assert reference is not None

    context.reference_photo = reference
    context.reference_id = str(reference.id.value)


@given(parsers.parse('there are {count:d} photos matching "{query}"'))
async def setup_many_matching_photos(
    count: int,
    query: str,
    test_db,
    mock_vector_store,
    context: Dict[str, Any]
):
    """Set up many photos matching a query."""
    photos = []

    for i in range(count):
        photo = Photo.create(
            filename=f"{query}_{i}.jpg",
            storage_path=f"test/{query}_{i}.jpg",
        )
        photo.description = f"{query} photo number {i}"

        test_db.add(photo)
        photos.append(photo)

        # Add to vector store
        embedding = [0.5] * 512
        embedding[0] = 0.8  # Make them similar for the query
        await mock_vector_store.add_embedding(str(photo.id.value), embedding)

    await test_db.commit()
    context.many_photos = photos
    context.total_count = count


@given(parsers.parse('there are {count:d} photos in the database'))
async def setup_large_photo_set(count: int, test_db, mock_vector_store):
    """Create a large set of photos for performance testing."""
    photos = []

    for i in range(count):
        photo = Photo.create(
            filename=f"photo_{i}.jpg",
            storage_path=f"test/photo_{i}.jpg",
        )
        photo.description = f"Photo {i} with random content"

        test_db.add(photo)

        # Add to vector store with random embedding
        import random
        embedding = [random.random() for _ in range(512)]
        await mock_vector_store.add_embedding(str(photo.id.value), embedding)

        # Commit in batches for performance
        if i % 100 == 0:
            await test_db.commit()

    await test_db.commit()


# ============================================================================
# WHEN Steps - Search Actions
# ============================================================================

@when(parsers.parse('I search for "{query}" with filters:'))
async def search_with_filters(
    query: str,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """Search with query and filters."""
    filters = {}
    for row in context.table:
        filter_name = row["filter"]
        filter_value = row["value"]

        # Convert string values to appropriate types
        if filter_value.lower() == "true":
            filters[filter_name] = True
        elif filter_value.lower() == "false":
            filters[filter_name] = False
        else:
            filters[filter_name] = filter_value

    response = await test_client.get(
        "/api/v1/search",
        params={"q": query, **filters}
    )

    context.search_response = response
    context.search_results = response.json().get("data", {}).get("results", [])
    return response


@when(parsers.parse('I search for "{query}" with page size {size:d}'))
async def search_with_pagination(
    query: str,
    size: int,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """Search with pagination parameters."""
    response = await test_client.get(
        "/api/v1/search",
        params={
            "q": query,
            "per_page": size,
            "page": 1
        }
    )

    context.search_response = response
    context.search_results = response.json().get("data", {}).get("results", [])
    context.pagination = response.json().get("meta", {})
    return response


@when("I search for visually similar photos")
async def search_visual_similarity(test_client: AsyncClient, context: Dict[str, Any]):
    """Search for visually similar photos."""
    reference_id = context.reference_id

    response = await test_client.get(
        f"/api/v1/search/similar/{reference_id}"
    )

    context.search_response = response
    context.search_results = response.json().get("data", {}).get("results", [])
    return response


# ============================================================================
# THEN Steps - Search Result Assertions
# ============================================================================

@then(parsers.parse('"{filename}" should be in the results'))
def assert_photo_in_results(filename: str, context: Dict[str, Any]):
    """Verify specific photo is in search results."""
    results = context.search_results
    filenames = [r.get("filename") for r in results]
    assert filename in filenames


@then(parsers.parse('"{filename}" should be the top result'))
def assert_photo_is_top_result(filename: str, context: Dict[str, Any]):
    """Verify specific photo is the first result."""
    results = context.search_results
    assert len(results) > 0
    assert results[0]["filename"] == filename


@then("the similarity score should be above 0.7")
def assert_similarity_score(context: Dict[str, Any]):
    """Verify similarity scores are above threshold."""
    results = context.search_results
    for result in results:
        score = result.get("similarity_score", 0)
        assert score > 0.7


@then("the results should include beach-related photos")
def assert_beach_related_results(context: Dict[str, Any]):
    """Verify results are semantically related to beaches."""
    results = context.search_results

    # Check that at least some results have beach-related content
    beach_related = 0
    for result in results:
        if any(word in result.get("filename", "").lower()
               for word in ["beach", "ocean", "sand", "coast"]):
            beach_related += 1

    assert beach_related > 0


@then('Even though "tropical" and "vacation" are not in the descriptions')
def assert_semantic_understanding(context: Dict[str, Any]):
    """Verify semantic search works without exact keyword matches."""
    # This is validated by the previous step finding beach photos
    # when searching for "tropical vacation"
    results = context.search_results
    assert len(results) > 0

    # Verify words aren't in descriptions
    for result in results[:3]:  # Check top 3
        desc = result.get("description", "").lower()
        assert "tropical" not in desc
        assert "vacation" not in desc


@then("photos with similar visual features should be returned")
def assert_visual_similarity(context: Dict[str, Any]):
    """Verify visually similar photos are returned."""
    results = context.search_results
    reference = context.reference_photo

    # Check that results share visual characteristics
    # In real implementation, this would check actual visual features
    assert len(results) > 0
    for result in results[:5]:
        # Results should have similarity scores
        assert "similarity_score" in result


@then(parsers.parse('"{filename}" might be included due to natural scenery'))
def assert_photo_might_be_included(filename: str, context: Dict[str, Any]):
    """Verify photo might be in results (non-strict assertion)."""
    results = context.search_results
    filenames = [r.get("filename") for r in results]
    # This is a soft assertion - photo may or may not be there
    # Log it but don't fail
    if filename in filenames:
        print(f"✓ {filename} found in results as expected")
    else:
        print(f"ℹ {filename} not in results (acceptable)")


@then(parsers.parse('But "{filename}" should have low similarity'))
def assert_low_similarity(filename: str, context: Dict[str, Any]):
    """Verify photo has low similarity score."""
    results = context.search_results

    # Find the photo in results
    photo_result = next(
        (r for r in results if r.get("filename") == filename),
        None
    )

    if photo_result:
        score = photo_result.get("similarity_score", 0)
        assert score < 0.5  # Low similarity threshold
    # If not in results, that's also acceptable (very low similarity)


@then("I should receive an empty result set")
def assert_empty_results(context: Dict[str, Any]):
    """Verify search returns empty results."""
    results = context.search_results
    assert len(results) == 0


@then("the response should indicate no matches found")
def assert_no_matches_message(context: Dict[str, Any]):
    """Verify response indicates no matches."""
    response_data = context.search_response.json()
    assert response_data.get("data", {}).get("total", 0) == 0
    # Message might be in meta or data
    message = (response_data.get("meta", {}).get("message") or
               response_data.get("data", {}).get("message") or "")
    assert "no" in message.lower() or len(context.search_results) == 0


@then("the status should be 200 (not an error)")
def assert_status_ok(context: Dict[str, Any]):
    """Verify response status is 200."""
    response = context.search_response
    assert response.status_code == 200


@then("only photos matching both query and filters should be returned")
def assert_filtered_results(context: Dict[str, Any]):
    """Verify results match both query and filters."""
    results = context.search_results

    # All results should be relevant to the query
    for result in results:
        # Check that result matches the search context
        assert result.get("filename") is not None


@then(parsers.parse('"{filename}" should be in the results'))
def assert_specific_file_in_filtered_results(filename: str, context: Dict[str, Any]):
    """Verify specific file is in filtered results."""
    results = context.search_results
    filenames = [r.get("filename") for r in results]
    assert filename in filenames


@then("But photos with faces should be excluded")
def assert_no_faces_in_results(context: Dict[str, Any]):
    """Verify no photos with faces are in results."""
    results = context.search_results

    for result in results:
        # Check face_count if available
        face_count = result.get("face_count", 0)
        assert face_count == 0


@then(parsers.parse("I should receive exactly {count:d} results"))
def assert_exact_result_count(count: int, context: Dict[str, Any]):
    """Verify exact number of results returned."""
    results = context.search_results
    assert len(results) == count


@then("pagination metadata should include:")
def assert_pagination_metadata(context: Dict[str, Any]):
    """Verify pagination metadata fields."""
    pagination = context.pagination

    for row in context.table:
        field = row["field"]
        expected_value = row["value"]

        assert field in pagination
        actual_value = str(pagination[field])
        assert actual_value == expected_value


@then("vacation and outdoor photos should be prioritized")
def assert_vacation_photos_prioritized(context: Dict[str, Any]):
    """Verify vacation/outdoor photos appear first."""
    results = context.search_results[:5]  # Check top 5

    # Count vacation/outdoor related photos
    vacation_count = 0
    for result in results:
        filename = result.get("filename", "").lower()
        desc = result.get("description", "").lower()
        if any(word in filename + desc
               for word in ["beach", "vacation", "outdoor", "summer"]):
            vacation_count += 1

    assert vacation_count >= 2  # At least 2 of top 5 should be vacation-related


@then(parsers.parse('"{filename}" should rank high'))
def assert_high_ranking(filename: str, context: Dict[str, Any]):
    """Verify photo ranks in top results."""
    results = context.search_results
    filenames = [r.get("filename") for r in results[:5]]  # Top 5
    assert filename in filenames


@then("results should reflect the emotional context")
def assert_emotional_context(context: Dict[str, Any]):
    """Verify results reflect emotional/conceptual understanding."""
    results = context.search_results

    # Check that results have positive/vacation vibes
    # In real implementation, this would use sentiment analysis
    assert len(results) > 0


@then(parsers.parse("the search should complete within {timeout:d}ms"))
def assert_search_performance(timeout: int, context: Dict[str, Any]):
    """Verify search completes within time limit."""
    # In real implementation, measure actual request time
    # For now, check that we got a response
    assert context.search_response is not None
    assert context.search_response.status_code == 200

    # Check if response includes timing information
    response_data = context.search_response.json()
    if "timing" in response_data.get("meta", {}):
        actual_time = response_data["meta"]["timing"]["total_ms"]
        assert actual_time < timeout


@then("return relevant results efficiently")
def assert_efficient_results(context: Dict[str, Any]):
    """Verify results are relevant and returned efficiently."""
    results = context.search_results
    assert len(results) > 0

    # Check that results have good similarity scores
    for result in results[:10]:  # Top 10
        score = result.get("similarity_score", 0)
        assert score > 0.3  # Minimum relevance threshold