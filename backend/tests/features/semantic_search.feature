Feature: Semantic Photo Search
  As a user
  I want to search photos using natural language
  So that I can find photos without exact keywords

  Background:
    Given the vector database is initialized
    And I have uploaded the following photos with descriptions:
      | filename      | description                     | tags                    |
      | beach.jpg     | sunset at the beach            | ocean, sunset, sand     |
      | mountain.jpg  | snowy mountain peaks           | snow, mountain, winter  |
      | dog.jpg       | golden retriever playing       | dog, pet, outdoor       |
      | city.jpg      | urban skyline at night         | city, night, buildings  |
      | forest.jpg    | dense green forest             | trees, nature, green    |

  @search @semantic @critical
  Scenario: Search with natural language query
    When I search for "ocean sunset"
    Then "beach.jpg" should be in the results
    And results should be ranked by semantic similarity
    And the similarity score should be above 0.7

  @search @semantic
  Scenario: Find conceptually similar photos
    When I search for "tropical vacation"
    Then "beach.jpg" should be the top result
    And the results should include beach-related photos
    Even though "tropical" and "vacation" are not in the descriptions

  @search @visual
  Scenario: Search with visual similarity
    Given I select "mountain.jpg" as the reference photo
    When I search for visually similar photos
    Then photos with similar visual features should be returned
    And "forest.jpg" might be included due to natural scenery
    But "city.jpg" should have low similarity

  @search @empty
  Scenario: Handle empty search results gracefully
    When I search for "spacecraft on mars"
    Then I should receive an empty result set
    And the response should indicate no matches found
    And the status should be 200 (not an error)

  @search @filter
  Scenario: Search with metadata filters
    When I search for "nature" with filters:
      | filter        | value           |
      | date_from     | 2024-01-01      |
      | date_to       | 2024-12-31      |
      | has_faces     | false           |
    Then only photos matching both query and filters should be returned
    And "forest.jpg" should be in the results
    But photos with faces should be excluded

  @search @pagination
  Scenario: Paginate search results
    Given there are 50 photos matching "outdoor"
    When I search for "outdoor" with page size 10
    Then I should receive exactly 10 results
    And pagination metadata should include:
      | field         | value |
      | total         | 50    |
      | page          | 1     |
      | per_page      | 10    |
      | total_pages   | 5     |

  @search @multilingual
  Scenario: Search in different languages
    When I search for "playa" (Spanish for beach)
    Then "beach.jpg" should be in the results
    Because the semantic model understands multilingual concepts

  @search @complex
  Scenario: Complex semantic query
    When I search for "happy memories from summer holidays"
    Then vacation and outdoor photos should be prioritized
    And "beach.jpg" should rank high
    And results should reflect the emotional context

  @search @performance
  Scenario: Fast search response
    Given there are 10000 photos in the database
    When I search for "sunset"
    Then the search should complete within 500ms
    And return relevant results efficiently