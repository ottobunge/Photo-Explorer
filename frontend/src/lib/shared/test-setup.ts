// Test setup for Vitest

import '@testing-library/svelte';

// Mock fetch globally
global.fetch = vi.fn();

// Reset mocks between tests
beforeEach(() => {
	vi.clearAllMocks();
});
