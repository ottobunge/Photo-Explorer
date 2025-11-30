"""Test runner for BDD features.

This file is needed for pytest-bdd to discover and run the feature files.
Each feature file needs to be explicitly loaded here.
"""

from pytest_bdd import scenarios

# Import all step definitions to ensure they're registered
from tests.features.steps.common import *
from tests.features.steps.photo_upload_steps import *
from tests.features.steps.search_steps import *
from tests.features.steps.face_steps import *
from tests.features.steps.album_steps import *
from tests.features.steps.folder_steps import *

# Load all feature files
scenarios("tests/features/photo_upload.feature")
scenarios("tests/features/semantic_search.feature")
scenarios("tests/features/face_tagging.feature")
scenarios("tests/features/album_management.feature")
scenarios("tests/features/folder_sync.feature")