Feature: Photo Upload
  As a user
  I want to upload photos to my collection
  So that I can organize and search through them

  Background:
    Given I am on the upload page

  Scenario: Upload page loads successfully
    Then I should see the upload zone
    And I should not see any server errors

  Scenario: Upload zone displays clear instructions
    Then the upload zone should display upload instructions
    And the instructions should mention dragging or selecting files

  Scenario: Upload zone is accessible via keyboard
    When I focus on the upload zone
    Then the upload zone should be focused

  Scenario: Selected files are displayed before upload
    When I select a file named "test-photo.jpg"
    Then I should see "test-photo.jpg" in the selected files list

  Scenario: User can remove selected files
    When I select a file named "test-photo.jpg"
    And I click the remove button for "test-photo.jpg"
    Then I should not see "test-photo.jpg" in the selected files list

  Scenario: Upload button is disabled when no files selected
    Then the upload button should not be visible

  Scenario: Upload button appears when files are selected
    When I select a file named "test-photo.jpg"
    Then the upload button should be visible
    And the upload button should show "Upload 1 Photo"
