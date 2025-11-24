# Photo Explorer - Feature Specification

## Feature Overview

This document details each feature with user stories, acceptance criteria, and implementation notes.

---

## F1: Photo Upload

### User Stories

**US1.1**: As a user, I want to upload individual photos so that I can add them to my collection.

**US1.2**: As a user, I want to upload multiple photos at once so that I can quickly add many photos.

**US1.3**: As a user, I want to see upload progress so that I know how long it will take.

**US1.4**: As a user, I want to optionally select an album during upload so that photos are organized immediately.

### Acceptance Criteria

```gherkin
Feature: Photo Upload

  Scenario: Upload a single photo
    Given I am on the upload page
    When I select a single JPEG image
    And I click the upload button
    Then the photo should be uploaded
    And I should see a success message
    And the photo should appear in processing queue

  Scenario: Upload multiple photos
    Given I am on the upload page
    When I drag and drop 5 images onto the upload area
    Then I should see a progress bar for each image
    And all images should be uploaded
    And each image should appear in processing queue

  Scenario: Upload to specific album
    Given I am on the upload page
    And I have selected album "Summer 2024"
    When I upload a photo
    Then the photo should be added to "Summer 2024" album

  Scenario: Reject invalid file type
    Given I am on the upload page
    When I try to upload a PDF file
    Then I should see an error message "Invalid file type"
    And the file should not be uploaded
```

### Implementation Notes

- Supported formats: JPEG, PNG, WebP, HEIC
- Max file size: 50MB
- Chunked upload for files > 5MB
- Generate immediate thumbnail for preview

---

## F2: Folder Scanning

### User Stories

**US2.1**: As a user, I want to point to a folder on my computer so that photos are automatically imported.

**US2.2**: As a user, I want to enable recursive scanning so that subfolders are also included.

**US2.3**: As a user, I want automatic sync so that new photos added to the folder are imported.

**US2.4**: As a user, I want to create albums from subfolders so that folder structure is preserved.

### Acceptance Criteria

```gherkin
Feature: Folder Scanning

  Scenario: Register a folder for scanning
    Given I am on the folders configuration page
    When I enter path "/home/user/Pictures"
    And I enable recursive scanning
    And I click "Add Folder"
    Then the folder should be registered
    And initial scan should begin

  Scenario: Scan finds new photos
    Given I have registered folder "/home/user/Pictures"
    When the folder contains 100 new images
    And a scan is triggered
    Then all 100 images should be imported
    And processing should begin for each

  Scenario: Auto-create albums from subfolders
    Given I have registered folder "/home/user/Pictures" with auto-album enabled
    And the folder has subfolders "Vacation" and "Birthday"
    When scanning completes
    Then albums "Vacation" and "Birthday" should be created
    And photos should be assigned to respective albums

  Scenario: Detect file changes
    Given I have a registered folder with existing photos
    When I modify an image file in that folder
    And a sync is triggered
    Then the photo should be re-processed with new data
```

### Implementation Notes

- Use filesystem watcher for real-time sync
- Store file hashes to detect changes
- Handle symlinks carefully
- Validate paths are accessible

---

## F3: Semantic Search

### User Stories

**US3.1**: As a user, I want to search photos using natural language so that I can find photos without knowing filenames.

**US3.2**: As a user, I want to filter search results so that I can narrow down results.

**US3.3**: As a user, I want to see relevance scores so that I understand why photos matched.

### Acceptance Criteria

```gherkin
Feature: Semantic Search

  Scenario: Basic text search
    Given I have photos of beaches, mountains, and cities
    When I search for "ocean waves crashing"
    Then I should see beach photos
    And beach photos should rank higher than other photos

  Scenario: Search with filters
    Given I have photos from 2023 and 2024
    When I search for "birthday party"
    And I filter by year 2024
    Then I should only see 2024 birthday photos

  Scenario: Search with face filter
    Given I have photos with tagged faces
    When I search for "outdoor adventure"
    And I filter by person "John"
    Then I should see outdoor photos containing John

  Scenario: No results
    Given I have no photos of elephants
    When I search for "elephant in zoo"
    Then I should see "No matching photos found"
    And I should see suggestions for similar searches
```

### Implementation Notes

- CLIP model for text-to-embedding
- Qdrant for vector similarity search
- Combine vector search with metadata filters
- Cache common query embeddings

---

## F4: Face Detection and Clustering

### User Stories

**US4.1**: As a user, I want faces automatically detected so that I can find photos of people.

**US4.2**: As a user, I want similar faces grouped together so that I can tag them once.

**US4.3**: As a user, I want to assign names to face groups so that I can search by person.

### Acceptance Criteria

```gherkin
Feature: Face Detection

  Scenario: Detect faces in uploaded photo
    Given I upload a photo with 3 visible faces
    When processing completes
    Then 3 faces should be detected
    And each face should have a crop saved
    And each face should be assigned to a cluster

  Scenario: Cluster similar faces
    Given I have 10 photos of the same person
    When all photos are processed
    Then faces of that person should be in same cluster
    And cluster should have representative face image

  Scenario: Different people in different clusters
    Given I have photos of John and Jane
    When processing completes
    Then John's faces should be in one cluster
    And Jane's faces should be in a different cluster
```

---

## F5: Face Tagging and Management

### User Stories

**US5.1**: As a user, I want to name face clusters so that I can identify people.

**US5.2**: As a user, I want to merge clusters so that I can fix incorrect separations.

**US5.3**: As a user, I want to move faces between clusters so that I can fix incorrect groupings.

### Acceptance Criteria

```gherkin
Feature: Face Tagging

  Scenario: Name a face cluster
    Given I have an unnamed face cluster
    When I assign the name "John Doe"
    Then the cluster should be named "John Doe"
    And all photos with that face should be searchable by "John"

  Scenario: Merge face clusters
    Given I have two clusters that are the same person
    When I merge cluster A into cluster B
    Then all faces from A should move to B
    And cluster A should be deleted

  Scenario: Split a face from cluster
    Given a cluster has a face that doesn't belong
    When I split that face
    Then a new cluster should be created
    And the face should move to the new cluster

  Scenario: Move face to different cluster
    Given I have a face in the wrong cluster
    When I move it to the correct cluster
    Then the face should appear in the new cluster
    And be removed from the old cluster
```

---

## F6: Face Explorer View

### User Stories

**US6.1**: As a user, I want to see all face clusters so that I can manage them.

**US6.2**: As a user, I want to filter by named/unnamed clusters so that I can focus on tagging.

**US6.3**: As a user, I want to see all photos of a person so that I can verify clustering.

### Acceptance Criteria

```gherkin
Feature: Face Explorer

  Scenario: View all face clusters
    Given I have 50 face clusters
    When I navigate to Face Explorer
    Then I should see all 50 clusters
    And each cluster should show representative face and count

  Scenario: Filter unnamed clusters
    Given I have 30 named and 20 unnamed clusters
    When I filter by unnamed only
    Then I should see 20 clusters
    And all should be unnamed

  Scenario: View person's photos
    Given I have named cluster "John" with 25 photos
    When I click on John's cluster
    Then I should see all 25 photos containing John
    And John's face should be highlighted in each

  Scenario: Drag and drop merge
    Given I see two clusters side by side
    When I drag one cluster onto another
    Then I should see merge confirmation
    And accepting should merge the clusters
```

---

## F7: Dataset/Details View

### User Stories

**US7.1**: As a user, I want to see detailed information about a photo so that I can understand its content.

**US7.2**: As a user, I want to see EXIF metadata so that I know camera settings.

**US7.3**: As a user, I want to see AI-generated description so that I understand what the AI sees.

**US7.4**: As a user, I want to correct AI predictions so that I can improve accuracy.

### Acceptance Criteria

```gherkin
Feature: Photo Details

  Scenario: View photo metadata
    Given I have a photo taken with a DSLR
    When I open the photo details
    Then I should see camera model
    And I should see date taken
    And I should see location if available
    And I should see camera settings (ISO, aperture, etc.)

  Scenario: View AI analysis
    Given I have a processed photo
    When I open the photo details
    Then I should see AI-generated description
    And I should see detected objects
    And I should see scene type
    And I should see indoor/outdoor classification

  Scenario: View detected faces
    Given I have a photo with faces
    When I open the photo details
    Then I should see face thumbnails
    And I should see who each face is (if named)
    And I should be able to click to view that person

  Scenario: Correct scene classification
    Given AI classified a photo as "indoor"
    And it's actually outdoor
    When I change classification to "outdoor"
    Then the change should be saved
    And future searches should use corrected value
```

---

## F8: Albums Management

### User Stories

**US8.1**: As a user, I want to create albums so that I can organize my photos.

**US8.2**: As a user, I want to add photos to albums so that I can group related photos.

**US8.3**: As a user, I want to set album covers so that albums are visually identifiable.

### Acceptance Criteria

```gherkin
Feature: Albums

  Scenario: Create album
    Given I am on the albums page
    When I click "New Album"
    And I enter name "Beach Trip 2024"
    And I click save
    Then a new album should be created
    And it should appear in my albums list

  Scenario: Add photos to album
    Given I have an empty album "Beach Trip"
    And I am viewing search results
    When I select 5 photos
    And I click "Add to Album"
    And I select "Beach Trip"
    Then all 5 photos should be in "Beach Trip"

  Scenario: Set album cover
    Given I have album with photos
    When I right-click a photo
    And I select "Set as Cover"
    Then that photo should become the album cover

  Scenario: Remove photo from album
    Given a photo is in album "Beach Trip"
    When I remove it from the album
    Then it should not appear in "Beach Trip"
    And it should still exist in my collection
```

---

## Testing Requirements

### Backend Testing (pytest + pytest-bdd)

Each feature must have:
- Unit tests for service layer
- Integration tests for API endpoints
- BDD scenarios for user-facing behavior

### Frontend Testing (Vitest + Playwright)

Each feature must have:
- Unit tests for stores and utilities
- Component tests for UI components
- E2E tests for critical user flows

### Test Coverage Requirements

- Minimum 80% line coverage for backend
- Minimum 80% line coverage for frontend
- 100% coverage for critical paths (upload, search, face tagging)
