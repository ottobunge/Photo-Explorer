Feature: Face Detection and Tagging
  As a user
  I want to tag and name faces in photos
  So that I can search for photos of specific people

  Background:
    Given face detection service is enabled
    And the face clustering threshold is set to 0.6

  @faces @critical
  Scenario: Automatic face detection on upload
    Given I have a photo "group.jpg" with 3 visible faces
    When I upload the photo
    Then 3 faces should be detected
    And each face should have:
      | property      | type                |
      | bounding_box  | coordinates         |
      | embedding     | 512-dim vector      |
      | confidence    | float > 0.9         |
    And faces should be saved to the database

  @faces @clustering @critical
  Scenario: Automatic face clustering
    Given I have uploaded photos containing the same person:
      | filename      | person      | face_count |
      | john1.jpg     | John        | 1          |
      | john2.jpg     | John        | 1          |
      | john3.jpg     | John        | 1          |
    When the clustering algorithm runs
    Then faces of the same person should be grouped together
    And a single cluster should be created for John
    And the cluster should contain 3 faces

  @faces @naming @critical
  Scenario: Name a face cluster
    Given I have an unnamed face cluster with ID "cluster_123"
    And the cluster contains 5 faces
    When I name the cluster "Jane Doe"
    Then all faces in the cluster should be tagged with "Jane Doe"
    And the cluster name should be saved
    And I can search for photos containing "Jane Doe"

  @faces @merge @critical @atomic
  Scenario: Merge face clusters atomically
    Given I have two clusters that are the same person:
      | cluster_id  | name      | face_count |
      | cluster_1   | null      | 3          |
      | cluster_2   | "Bob"     | 5          |
    When I merge "cluster_1" into "cluster_2"
    Then the operation should be atomic
    And "cluster_1" should be deleted
    And "cluster_2" should contain 8 faces
    And all faces should be tagged with "Bob"
    And if any error occurs, changes should be rolled back

  @faces @split
  Scenario: Split incorrectly grouped faces
    Given I have a cluster "cluster_456" with 10 faces
    And 2 faces are incorrectly grouped
    When I select those 2 faces to split out
    Then a new cluster should be created with the 2 faces
    And the original cluster should have 8 faces
    And both clusters should be independent

  @faces @search @critical
  Scenario: Search photos by person name
    Given I have tagged clusters:
      | name          | photo_count |
      | Alice Smith   | 15          |
      | Bob Johnson   | 8           |
      | Charlie Brown | 12          |
    When I search for photos of "Alice Smith"
    Then I should receive all 15 photos containing Alice
    And results should be ordered by date taken
    And each result should indicate face locations

  @faces @privacy
  Scenario: Handle face detection opt-out
    Given a photo "private.jpg" is marked as private
    When I upload the photo
    Then face detection should be skipped
    And no face data should be stored
    But the photo should still be searchable by other means

  @faces @quality
  Scenario: Filter low-quality face detections
    Given I have a photo "blurry.jpg" with unclear faces
    When face detection runs
    Then only faces with confidence > 0.8 should be kept
    And low-confidence detections should be discarded
    And the user should be notified of skipped faces

  @faces @update
  Scenario: Update face cluster assignments
    Given a face is in cluster "cluster_old"
    When I reassign it to cluster "cluster_new"
    Then the face should be removed from "cluster_old"
    And added to "cluster_new"
    And cluster statistics should be updated

  @faces @delete
  Scenario: Delete face data while keeping photos
    Given I have a photo with detected faces
    When I request to delete face data for the photo
    Then all face records should be deleted
    But the photo should remain in the library
    And the photo should still be searchable by other attributes