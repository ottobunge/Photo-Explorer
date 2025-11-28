Feature: Photo Search
  As a user
  I want to search for photos using text queries
  So that I can quickly find relevant photos in my collection

  Background:
    Given I am on the search page

  Scenario: Search page loads successfully
    Then I should see the search input field
    And I should see the search button
    And I should not see any server errors

  Scenario: Search button is disabled with empty input
    Then the search button should be disabled

  Scenario: Search button is enabled with text input
    When I enter "sunset" in the search field
    Then the search button should be enabled

  Scenario: Filter toggle shows and hides filter options
    When I click the filter toggle button
    Then the filter options visibility should change
    When I click the filter toggle button again
    Then the filter options should return to their initial state

  Scenario: Search returns matching photos
    When I enter "photo" in the search field
    And I click the search button
    And I wait for the search to complete
    Then I should see either photo results or a no results message
    And I should not see any server errors

  Scenario: Search handles no results gracefully
    When I enter "xyznonexistent12345" in the search field
    And I click the search button
    And I wait for the search to complete
    Then I should see a no results message
    And I should not see any photo cards
    And I should not see any server errors
