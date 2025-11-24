#!/usr/bin/env python3
"""
Model download script for Photo Explorer.

Downloads CLIP and face detection models needed for the application.

Usage:
    python scripts/download_models.py --all
    python scripts/download_models.py --clip ViT-B-32
    python scripts/download_models.py --face buffalo_l
    python scripts/download_models.py --status
    python scripts/download_models.py --list
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.models.downloader import main

if __name__ == "__main__":
    main()
