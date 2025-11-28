import { Given, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';

/**
 * Common Step Definitions
 *
 * Reusable steps that can be used across multiple features.
 * These implement common user actions and assertions.
 */

// Navigation steps
Given('I am on the upload page', async ({ page }) => {
	await page.goto('/upload');
	await page.waitForLoadState('networkidle');
});

Given('I am on the faces page', async ({ page }) => {
	await page.goto('/faces');
	await page.waitForLoadState('networkidle');
});

Given('I am on the settings page', async ({ page }) => {
	await page.goto('/settings');
	await page.waitForLoadState('networkidle');
});

Given('I am on the albums page', async ({ page }) => {
	await page.goto('/albums');
	await page.waitForLoadState('networkidle');
});

// Common assertions
Then('I should not see any server errors', async ({ page }) => {
	await expect(page.getByText(/500/i)).not.toBeVisible();
	await expect(page.getByText(/server error/i)).not.toBeVisible();
	await expect(page.getByText(/internal server error/i)).not.toBeVisible();
});

Then('the page should load successfully', async ({ page }) => {
	// Verify page is loaded and interactive
	await page.waitForLoadState('networkidle');
	await page.waitForLoadState('domcontentloaded');

	// Verify no critical errors
	await expect(page.getByText(/500/i)).not.toBeVisible();
	await expect(page.getByText(/server error/i)).not.toBeVisible();
});

Then('I should see the page heading {string}', async ({ page }, heading: string) => {
	await expect(page.locator('h1', { hasText: heading })).toBeVisible();
});

// Waiting steps
Then('I wait for {int} milliseconds', async ({ page }, ms: number) => {
	await page.waitForTimeout(ms);
});

Then('I wait for the page to finish loading', async ({ page }) => {
	await page.waitForLoadState('networkidle');
});

// Click actions
Then('I click the {string} button', async ({ page }, buttonText: string) => {
	await page.getByRole('button', { name: new RegExp(buttonText, 'i') }).click();
});

Then('I click the element with test id {string}', async ({ page }, testId: string) => {
	await page.getByTestId(testId).click();
});

// Visibility checks
Then('I should see an element with test id {string}', async ({ page }, testId: string) => {
	await expect(page.getByTestId(testId)).toBeVisible();
});

Then('I should not see an element with test id {string}', async ({ page }, testId: string) => {
	await expect(page.getByTestId(testId)).not.toBeVisible();
});

Then('I should see text {string}', async ({ page }, text: string) => {
	await expect(page.getByText(text)).toBeVisible();
});

Then('I should not see text {string}', async ({ page }, text: string) => {
	await expect(page.getByText(text)).not.toBeVisible();
});
