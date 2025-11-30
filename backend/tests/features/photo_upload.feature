Feature: Photo Upload and Processing
  As a user
  I want to upload photos to my library
  So that I can search and organize them

  Background:
    Given the system is ready to accept uploads
    And ML services are available

  @upload @critical
  Scenario: Upload single photo successfully
    Given I have a valid image file "sunset.jpg"
    When I upload the photo
    Then the upload should be successful
    And the photo should be stored in the database
    And the photo should be indexed for search
    And metadata should be extracted from the photo
    And the response should include the photo ID

  @upload @faces
  Scenario: Upload photo with face detection
    Given face detection is enabled
    And I have a photo "family.jpg" containing faces
    When I upload the photo
    Then the upload should be successful
    And faces should be detected in the photo
    And face embeddings should be generated
    And faces should be added to clusters

  @upload @validation
  Scenario: Reject invalid file type
    Given I have a non-image file "document.pdf"
    When I attempt to upload the file
    Then the upload should be rejected with status 400
    And the error message should contain "Invalid file type"

  @upload @duplicate
  Scenario: Handle duplicate photos gracefully
    Given I have already uploaded "beach.jpg" with hash "abc123"
    When I upload the same photo again
    Then the system should detect the duplicate
    And return the existing photo ID
    And not create a duplicate entry

  @upload @batch
  Scenario: Upload multiple photos in batch
    Given I have multiple image files:
      | filename      | type    |
      | photo1.jpg    | image   |
      | photo2.png    | image   |
      | photo3.gif    | image   |
    When I upload all photos in batch
    Then all 3 photos should be uploaded successfully
    And each photo should have a unique ID
    And all photos should be processed asynchronously

  @upload @metadata
  Scenario: Extract and store photo metadata
    Given I have a photo "camera.jpg" with EXIF data
    When I upload the photo
    Then the upload should be successful
    And the following metadata should be extracted:
      | field         | value                |
      | camera_make   | Canon                |
      | camera_model  | EOS R5               |
      | taken_at      | 2024-03-15T10:30:00  |
      | gps_latitude  | 37.7749              |
      | gps_longitude | -122.4194            |

  @upload @error
  Scenario: Handle upload errors gracefully
    Given I have a corrupted image file "corrupted.jpg"
    When I attempt to upload the file
    Then the upload should fail with status 422
    And the error message should indicate "Cannot process image"
    And no partial data should be saved

  @upload @size
  Scenario: Reject files exceeding size limit
    Given I have an image file "huge.jpg" larger than 50MB
    When I attempt to upload the file
    Then the upload should be rejected with status 413
    And the error message should contain "File too large"