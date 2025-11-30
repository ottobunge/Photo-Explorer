Feature: Photo Album Management
  As a user
  I want to organize photos into albums
  So that I can group related photos together

  Background:
    Given I am authenticated as a user
    And I have photos in my library:
      | photo_id | filename        | date_taken  |
      | photo_1  | vacation1.jpg   | 2024-07-01  |
      | photo_2  | vacation2.jpg   | 2024-07-02  |
      | photo_3  | birthday1.jpg   | 2024-08-15  |
      | photo_4  | birthday2.jpg   | 2024-08-15  |
      | photo_5  | random.jpg      | 2024-09-01  |

  @albums @create @critical
  Scenario: Create a new album
    When I create an album named "Summer Vacation 2024"
    Then the album should be created successfully
    And the album should have a unique ID
    And the album should be empty initially
    And the creation timestamp should be recorded

  @albums @add @critical
  Scenario: Add photos to album
    Given I have an album "Summer Vacation 2024"
    When I add the following photos to the album:
      | photo_id |
      | photo_1  |
      | photo_2  |
    Then the album should contain 2 photos
    And the photos should remain in their original location
    And the photos should be associated with the album

  @albums @remove
  Scenario: Remove photos from album
    Given I have an album "Summer Vacation 2024" containing:
      | photo_id |
      | photo_1  |
      | photo_2  |
      | photo_5  |
    When I remove "photo_5" from the album
    Then the album should contain 2 photos
    And "photo_5" should remain in the library
    And "photo_5" should no longer be associated with the album

  @albums @delete
  Scenario: Delete album without deleting photos
    Given I have an album "Temporary Album" with 5 photos
    When I delete the album
    Then the album should be removed from the system
    But all 5 photos should remain in the library
    And the photos should be searchable
    And the album association should be removed from photos

  @albums @list
  Scenario: List all albums with pagination
    Given I have created 15 albums
    When I request albums with page size 10
    Then I should receive 10 albums
    And pagination metadata should show:
      | field       | value |
      | total       | 15    |
      | page        | 1     |
      | per_page    | 10    |
      | total_pages | 2     |

  @albums @duplicate
  Scenario: Prevent duplicate album names
    Given I have an album named "Family Photos"
    When I try to create another album named "Family Photos"
    Then the creation should fail with status 409
    And the error message should indicate "Album name already exists"

  @albums @rename
  Scenario: Rename an existing album
    Given I have an album named "Old Name"
    When I rename the album to "New Name"
    Then the album should be renamed successfully
    And all photo associations should be preserved
    And the album ID should remain the same

  @albums @share
  Scenario: Generate shareable album link
    Given I have an album "Public Gallery" with photos
    When I request a shareable link for the album
    Then a unique share URL should be generated
    And the link should have an optional expiration date
    And access permissions should be configurable

  @albums @stats
  Scenario: Get album statistics
    Given I have an album with 20 photos
    When I request album statistics
    Then I should receive:
      | statistic           | value      |
      | photo_count         | 20         |
      | total_size_mb       | 125.5      |
      | date_range          | 30 days    |
      | most_common_tag     | vacation   |

  @albums @cover
  Scenario: Set album cover photo
    Given I have an album "Travel" with multiple photos
    When I set "photo_3" as the cover photo
    Then "photo_3" should be displayed as the album cover
    And the cover setting should be saved
    And the album list should show the cover thumbnail

  @albums @batch
  Scenario: Batch operations on albums
    Given I have an album "Batch Test"
    When I perform a batch add of 50 photos
    Then all photos should be added in a single transaction
    And the operation should complete within 2 seconds
    And either all photos are added or none (atomic operation)

  @albums @auto
  Scenario: Auto-create album from folder import
    Given I import photos from a folder named "Christmas 2024"
    And the auto-album setting is enabled
    When the import completes
    Then an album named "Christmas 2024" should be created
    And all imported photos should be added to the album