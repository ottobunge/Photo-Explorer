#!/usr/bin/env bash
#
# Test script to verify photo upload flow
#

set -e

echo "=== Photo Explorer Upload Test ==="
echo

# Configuration
API_BASE="${API_BASE:-http://localhost:8000/api/v1}"
TEST_IMAGE="/tmp/test-photo.jpg"

# Create a simple test image if it doesn't exist
if [ ! -f "$TEST_IMAGE" ]; then
    echo "Creating test image..."
    # Create a 100x100 red square JPEG
    convert -size 100x100 xc:red "$TEST_IMAGE" 2>/dev/null || {
        echo "ImageMagick not found, downloading a test image..."
        curl -s -o "$TEST_IMAGE" "https://picsum.photos/200/300.jpg"
    }
fi

echo "Using test image: $TEST_IMAGE"
echo

# Step 1: Upload photo
echo "Step 1: Uploading photo..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_BASE/photos/upload" \
    -F "files=@$TEST_IMAGE" \
    -H "Accept: application/json")

echo "Upload response: $UPLOAD_RESPONSE"
echo

# Extract photo ID
PHOTO_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.data.uploaded[0].id' 2>/dev/null || echo "")

if [ -z "$PHOTO_ID" ] || [ "$PHOTO_ID" = "null" ]; then
    echo "ERROR: Failed to extract photo ID from upload response"
    exit 1
fi

echo "Photo uploaded with ID: $PHOTO_ID"
echo

# Step 2: Wait for processing
echo "Step 2: Waiting for photo processing (5 seconds)..."
sleep 5
echo

# Step 3: Get photo metadata
echo "Step 3: Fetching photo metadata..."
PHOTO_RESPONSE=$(curl -s "$API_BASE/photos/$PHOTO_ID")
echo "Photo metadata: $PHOTO_RESPONSE" | jq '.' 2>/dev/null || echo "$PHOTO_RESPONSE"
echo

# Step 4: Try to get the photo file
echo "Step 4: Fetching photo file..."
HTTP_CODE=$(curl -s -o /tmp/downloaded-photo.jpg -w "%{http_code}" "$API_BASE/photos/$PHOTO_ID/file")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ SUCCESS: Photo file downloaded (HTTP $HTTP_CODE)"
    echo "File saved to: /tmp/downloaded-photo.jpg"
    ls -lh /tmp/downloaded-photo.jpg
else
    echo "❌ FAILED: Could not download photo file (HTTP $HTTP_CODE)"
    cat /tmp/downloaded-photo.jpg
    exit 1
fi
echo

# Step 5: Try to get the thumbnail
echo "Step 5: Fetching thumbnail..."
HTTP_CODE=$(curl -s -o /tmp/downloaded-thumbnail.jpg -w "%{http_code}" "$API_BASE/photos/$PHOTO_ID/thumbnail")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ SUCCESS: Thumbnail downloaded (HTTP $HTTP_CODE)"
    echo "File saved to: /tmp/downloaded-thumbnail.jpg"
    ls -lh /tmp/downloaded-thumbnail.jpg
else
    echo "❌ FAILED: Could not download thumbnail (HTTP $HTTP_CODE)"
    cat /tmp/downloaded-thumbnail.jpg
fi
echo

echo "=== Test Complete ===" echo
echo "Photo ID: $PHOTO_ID"
echo "You can view the photo at: http://localhost:5173/photos/$PHOTO_ID"
