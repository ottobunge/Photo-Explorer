import { test as base } from 'playwright-bdd';

/**
 * Custom fixtures for Photo Explorer E2E tests.
 * Extend this file with any reusable test fixtures.
 */

// For now, export the base test unchanged.
// As we build our step definitions, we can add custom fixtures here.
export const test = base;
export { expect } from '@playwright/test';
