# Test Dataset for Semantic Search

This document describes the test image dataset used for E2E testing of semantic search functionality.

## Overview

The test dataset consists of **20 animal photos** (5 each of cats, dogs, raccoons, and ferrets) sourced from Unsplash under the Unsplash License.

## Key Features

✅ **Automatic Download** - Images are downloaded automatically when tests run
✅ **Not Committed** - Images are excluded from git via .gitignore
✅ **Semantic Diversity** - Different animals to test semantic understanding
✅ **License Compliant** - All images free to use under Unsplash License

## Dataset Structure

```
backend/tests/fixtures/images/
├── cats/
│   ├── cat_1.jpg
│   ├── cat_2.jpg
│   ├── cat_3.jpg
│   ├── cat_4.jpg
│   └── cat_5.jpg
├── dogs/
│   ├── dog_1.jpg
│   ├── dog_2.jpg
│   ├── dog_3.jpg
│   ├── dog_4.jpg
│   └── dog_5.jpg
├── raccoons/
│   ├── raccoon_1.jpg
│   ├── raccoon_2.jpg
│   ├── raccoon_3.jpg
│   ├── raccoon_4.jpg
│   └── raccoon_5.jpg
└── ferrets/
    ├── ferret_1.jpg
    ├── ferret_2.jpg
    ├── ferret_3.jpg
    ├── ferret_4.jpg
    └── ferret_5.jpg
```

## Usage

### Automatic (Recommended)

Test fixtures will automatically download images when you run tests:

```bash
pytest backend/tests/e2e/
```

The `test_images_dir` fixture checks if images exist and downloads them if needed.

### Manual Download

To download images manually:

```bash
cd backend/tests/fixtures
python download_test_images.py
```

### Using in Tests

Import fixtures in your tests:

```python
from tests.fixtures.conftest import (
    test_images_dir,
    cat_images,
    dog_images,
    raccoon_images,
    ferret_images,
    all_test_images,
)

def test_semantic_search(cat_images):
    # cat_images is a list of Path objects
    for img_path in cat_images:
        with open(img_path, "rb") as f:
            image_data = f.read()
        # Use image_data for testing
```

## Test Coverage

The dataset enables testing of:

### 1. **Basic Semantic Search**
- Query: "a cat" → Returns cat images
- Query: "a dog" → Returns dog images
- Verifies CLIP embeddings work correctly

### 2. **Animal Classification**
- Distinguishes between different animal types
- Verifies semantic understanding

### 3. **Similarity Search**
- Query with cat image → Returns other cat images ranked higher than dogs
- Tests visual similarity

### 4. **Semantic Understanding**
- Query: "feline" → Returns cat images
- Query: "puppy" → Returns dog images
- Query: "canine" → Returns dog images
- Tests semantic relationships, not just keywords

### 5. **Full Pipeline**
- Upload → Thumbnail → Embedding → Index → Search
- End-to-end workflow validation

## E2E Test Files

### `backend/tests/e2e/test_semantic_search.py`
- ✅ Search for cats finds cat images
- ✅ Semantic search distinguishes between animals
- ✅ Similar image search ranks correctly
- ✅ Semantic understanding (feline=cat, puppy=dog)

### `backend/tests/e2e/test_local_file_upload.py`
- ✅ Upload generates thumbnail
- ✅ Upload generates CLIP embedding
- ✅ Batch upload and search
- ✅ Full pipeline with real file

## Image Sources

All images are from [Unsplash](https://unsplash.com) and are free to use under the [Unsplash License](https://unsplash.com/license).

- **No attribution required** for use
- **Free for commercial and non-commercial use**
- **Do not redistribute as part of a stock photo service**

Image URLs are hardcoded in `download_test_images.py` for reproducibility.

## Maintenance

### Updating Images

To change the image set, edit `download_test_images.py`:

```python
TEST_IMAGES = {
    "cats": [
        ("cat_1.jpg", "https://images.unsplash.com/photo-...?w=800"),
        # Add more images
    ],
}
```

### Verifying Downloads

The download script validates downloads with:
- ✅ HTTP status checks
- ✅ MD5 checksums (logged)
- ✅ Retry logic (3 attempts)
- ✅ File size verification

### Cleanup

To remove downloaded images:

```bash
rm -rf backend/tests/fixtures/images/
```

Images will be re-downloaded on next test run.

## Git Ignore

Images are excluded from git via `.gitignore`:

```gitignore
# Test fixtures - images (downloaded at test time)
backend/tests/fixtures/images/
**/test_images/
**/fixtures/images/
```

**Important:** Never commit test images to the repository. They should be downloaded dynamically during test execution.

## File Size

- Each image: ~50-200KB (800px wide from Unsplash)
- Total dataset: ~2-4MB
- Download time: ~5-10 seconds

## CI/CD Integration

For CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Download test images
  run: |
    cd backend/tests/fixtures
    python download_test_images.py

- name: Run E2E tests
  run: |
    pytest backend/tests/e2e/ -v
```

Or rely on automatic download via test fixtures (recommended).

## Troubleshooting

### Download Fails

If downloads fail:
1. Check internet connection
2. Verify Unsplash URLs are still valid
3. Check for rate limiting (wait and retry)
4. Run script manually to see detailed errors

### Images Not Found

```python
FileNotFoundError: No such file or directory: 'images/cats/cat_1.jpg'
```

**Solution:** Run download script or let fixtures download automatically:
```bash
python backend/tests/fixtures/download_test_images.py
```

### Test Fixture Errors

```python
pytest.fail: Failed to download test images
```

**Solution:** Check script output in pytest logs, fix network/URL issues.

## Performance

- **First run:** 5-10 seconds (download images)
- **Subsequent runs:** <1 second (images cached)
- **CI/CD:** Consider caching `backend/tests/fixtures/images/` directory

## Future Enhancements

Potential additions to test dataset:
- [ ] More animal varieties (birds, fish, etc.)
- [ ] Indoor/outdoor scenes for scene classification
- [ ] Faces for face detection testing
- [ ] Different image qualities/sizes
- [ ] Edge cases (corrupted images, non-photos)

## Summary

The test dataset provides a comprehensive, automatically-managed set of images for validating semantic search functionality. It's designed to be:

- **Developer-friendly:** Automatic download, no manual setup
- **CI/CD-ready:** Works in automated pipelines
- **License-compliant:** Free to use, no legal issues
- **Semantically diverse:** Tests real-world search scenarios
- **Maintainable:** Easy to update and extend

For questions or issues, see `TESTING_AND_DEPLOYMENT_PLAN.md`.
