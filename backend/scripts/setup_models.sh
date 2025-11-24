#!/usr/bin/env bash
#
# Setup script for Photo Explorer AI models
#
# This script downloads and configures the required AI models:
# - CLIP model for semantic image search
# - InsightFace model for face detection
#
# Usage:
#   ./scripts/setup_models.sh           # Download default models
#   ./scripts/setup_models.sh --all     # Download all available models
#   ./scripts/setup_models.sh --status  # Check model status
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║          Photo Explorer - Model Setup                ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python is not installed or not in PATH${NC}"
    exit 1
fi

# Check if we're in a virtual environment or if dependencies are installed
cd "$BACKEND_DIR"

if [ ! -f ".venv/bin/activate" ] && [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: No virtual environment found.${NC}"
    echo "Creating virtual environment..."
    python -m venv .venv
    source .venv/bin/activate
    echo "Installing dependencies..."
    pip install -e ".[dev]"
elif [ -f ".venv/bin/activate" ] && [ -z "$VIRTUAL_ENV" ]; then
    source .venv/bin/activate
fi

# Check for required packages
python -c "import httpx" 2>/dev/null || {
    echo -e "${YELLOW}Installing required packages...${NC}"
    pip install httpx
}

# Parse arguments
if [ "$1" == "--status" ]; then
    echo -e "\n${BLUE}Checking model status...${NC}\n"
    python scripts/download_models.py --status
    exit 0
fi

if [ "$1" == "--list" ]; then
    echo -e "\n${BLUE}Available models:${NC}\n"
    python scripts/download_models.py --list
    exit 0
fi

if [ "$1" == "--all" ]; then
    echo -e "\n${BLUE}Downloading all configured models...${NC}\n"
    python scripts/download_models.py --all
    exit 0
fi

# Default: download configured models
echo -e "\n${BLUE}Downloading required models...${NC}\n"
echo "This may take a few minutes depending on your internet connection."
echo ""

# Download CLIP model
echo -e "${YELLOW}[1/2] Downloading CLIP model (ViT-B-32)...${NC}"
if python scripts/download_models.py --clip ViT-B-32; then
    echo -e "${GREEN}✓ CLIP model downloaded successfully${NC}"
else
    echo -e "${RED}✗ Failed to download CLIP model${NC}"
    echo "You can try again later with: task models:download:clip"
fi

echo ""

# Download face detection model
echo -e "${YELLOW}[2/2] Downloading face detection model (buffalo_l)...${NC}"
if python scripts/download_models.py --face buffalo_l; then
    echo -e "${GREEN}✓ Face detection model downloaded successfully${NC}"
else
    echo -e "${RED}✗ Failed to download face detection model${NC}"
    echo "You can try again later with: task models:download:face"
fi

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   Setup Complete                     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Show final status
python scripts/download_models.py --status
