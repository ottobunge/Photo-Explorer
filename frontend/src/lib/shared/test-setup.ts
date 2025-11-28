// Test setup for Vitest

import '@testing-library/svelte';
import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Configure jsdom for Svelte 5
// This ensures proper DOM environment for Svelte component rendering
if (typeof window !== 'undefined') {
	// Set up custom element registry if not already present
	if (!window.customElements) {
		(window as any).customElements = {
			define: () => {},
			get: () => undefined,
			whenDefined: () => Promise.resolve()
		};
	}
}

// Mock fetch globally
global.fetch = vi.fn();

// Reset mocks between tests
beforeEach(() => {
	vi.clearAllMocks();
});
