/**
 * Mock for $app/stores in tests
 */

import { readable } from 'svelte/store';

// Mock page store with empty default
export const page = readable({
	url: new URL('http://localhost'),
	params: {},
	route: { id: null },
	status: 200,
	error: null,
	data: {},
	state: {},
	form: undefined
});

// Mock navigating store
export const navigating = readable(null);

// Mock updated store
export const updated = readable(false);
