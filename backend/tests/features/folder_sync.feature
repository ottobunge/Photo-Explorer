Feature: Local Folder Synchronization
  As a user
  I want to sync local folders with the photo library
  So that new photos are automatically imported

  Background:
    Given the file system watcher is enabled
    And I have a test folder structure:
      | path                          | type   | content      |
      | /photos/camera/               | folder |              |
      | /photos/camera/img001.jpg     | file   | valid image  |
      | /photos/camera/img002.jpg     | file   | valid image  |
      | /photos/archive/              | folder |              |
      | /photos/archive/old001.jpg    | file   | valid image  |

  @sync @register @critical
  Scenario: Register folder for watching
    When I register "/photos/camera" for watching
    Then the folder should be added to watched folders
    And existing photos should be scanned immediately
    And 2 photos should be imported from the initial scan
    And the folder status should be "watching"

  @sync @detect @critical
  Scenario: Detect new photos automatically
    Given I am watching folder "/photos/camera"
    When I add a new photo "img003.jpg" to the folder
    Then the photo should be detected within 5 seconds
    And the photo should be automatically imported
    And the photo should be processed like an uploaded photo
    And the source path should be recorded

  @sync @delete
  Scenario: Handle deleted photos from folder
    Given I am watching folder "/photos/camera"
    And "img001.jpg" has been imported from this folder
    When I delete "img001.jpg" from the folder
    Then the photo should be marked as "source_deleted" in the database
    But the photo should remain in the photo library
    And thumbnails and processed data should be retained

  @sync @ignore
  Scenario: Skip non-image files
    Given I am watching folder "/photos/camera"
    When I add these files to the folder:
      | filename      | type        |
      | document.pdf  | document    |
      | video.mp4     | video       |
      | photo.jpg     | image       |
      | readme.txt    | text        |
    Then only "photo.jpg" should be imported
    And other files should be ignored
    And no errors should be logged for ignored files

  @sync @recursive @critical
  Scenario: Handle nested folders recursively
    Given I register "/photos" with recursive watching enabled
    When I add a photo to "/photos/nested/deep/folder/photo.jpg"
    Then the photo should be detected and imported
    And the full path structure should be preserved
    And parent folders should be created if needed

  @sync @duplicate
  Scenario: Handle duplicate files across folders
    Given I am watching both "/photos/camera" and "/photos/archive"
    And both folders contain "same.jpg" with identical content
    When both folders are scanned
    Then only one instance should be imported
    And the duplicate should be detected by hash
    And both source paths should be recorded

  @sync @pause
  Scenario: Pause and resume folder watching
    Given I am watching folder "/photos/camera"
    When I pause watching for this folder
    And I add "new_photo.jpg" to the folder
    Then the photo should not be imported
    When I resume watching
    Then pending changes should be detected
    And "new_photo.jpg" should be imported

  @sync @unregister
  Scenario: Unregister folder from watching
    Given I am watching folder "/photos/camera"
    When I unregister the folder
    Then the folder should be removed from watched folders
    But previously imported photos should remain
    And new photos added should not be imported

  @sync @modify
  Scenario: Detect modified photos
    Given I am watching folder "/photos/camera"
    And "photo.jpg" has been imported
    When I replace "photo.jpg" with a modified version
    Then the change should be detected
    And the photo should be re-processed
    And the updated version should replace the original

  @sync @error
  Scenario: Handle inaccessible folders gracefully
    Given I register "/photos/restricted" for watching
    When the folder becomes inaccessible due to permissions
    Then an error should be logged
    And the folder status should be "error"
    But the system should continue watching other folders
    And retry should be attempted periodically

  @sync @performance
  Scenario: Handle large folder efficiently
    Given I have a folder "/photos/large" with 10000 images
    When I register the folder for watching
    Then the initial scan should use batch processing
    And memory usage should remain below 500MB
    And progress should be reported periodically
    And the scan should complete within 5 minutes

  @sync @filter
  Scenario: Apply filters during folder sync
    Given I register "/photos/camera" with filters:
      | filter          | value           |
      | min_size_kb     | 100            |
      | max_size_mb     | 20             |
      | extensions      | jpg,png,heic   |
      | modified_after  | 2024-01-01     |
    When the folder is scanned
    Then only photos matching all filters should be imported
    And filtered photos should be logged as skipped