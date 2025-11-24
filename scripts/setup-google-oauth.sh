#!/usr/bin/env bash
# Setup script for Google OAuth configuration
# Run from project root: ./scripts/setup-google-oauth.sh

set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-photo-explorer-479210}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

echo "=== Google OAuth Setup for Photo Explorer ==="
echo "Project: $PROJECT_ID"
echo ""

# Check if logged in
if ! gcloud auth print-access-token &>/dev/null; then
    echo "Not logged in to gcloud. Running: gcloud auth login"
    gcloud auth login
fi

# Set project
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable photoslibrary.googleapis.com
gcloud services enable oauth2.googleapis.com

echo ""
echo "=== APIs Enabled ==="
gcloud services list --enabled --filter="NAME:(photo* OR oauth*)" --format="table(NAME)"

echo ""
echo "=== Manual Configuration Required ==="
echo ""
echo "Please configure the following in Google Cloud Console:"
echo "https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
echo ""
echo "1. OAuth Consent Screen (if not configured):"
echo "   - User Type: External (or Internal for Workspace)"
echo "   - App name: Photo Explorer"
echo "   - Support email: your email"
echo "   - Scopes: Add 'https://www.googleapis.com/auth/photoslibrary.readonly'"
echo ""
echo "2. OAuth 2.0 Client IDs - Add these Authorized redirect URIs:"
echo ""
echo "   For Web Client:"
echo "   - $FRONTEND_URL/settings/connectors/google/callback"
echo "   - $FRONTEND_URL/auth/google/callback"
echo ""
echo "   For Desktop Client (if using OAuth playground for testing):"
echo "   - https://developers.google.com/oauthplayground"
echo ""
echo "3. For production, also add your production URLs"
echo ""

# Print current .env values
if [ -f .env ]; then
    echo "=== Current .env Configuration ==="
    grep -E "^GOOGLE_" .env 2>/dev/null || echo "No GOOGLE_ variables found"
fi

echo ""
echo "=== Quick Test ==="
echo "To test the OAuth flow manually, visit:"
echo "https://developers.google.com/oauthplayground"
echo "- Click settings gear, check 'Use your own OAuth credentials'"
echo "- Enter your Client ID and Secret"
echo "- Select 'Photos Library API v1' -> '.../auth/photoslibrary.readonly'"
echo "- Click 'Authorize APIs' and complete the flow"
