/**
 * Mock implementations for common dependencies used in tests
 */

import { vi } from 'vitest';
import type { ApiResponse } from '$lib/types';

/**
 * Mock API client with common methods
 */
export const mockApiClient = {
	get: vi.fn().mockResolvedValue({ success: true, data: {} }),
	post: vi.fn().mockResolvedValue({ success: true, data: {} }),
	patch: vi.fn().mockResolvedValue({ success: true, data: {} }),
	delete: vi.fn().mockResolvedValue({ success: true, data: {} }),
	postForm: vi.fn().mockResolvedValue({ success: true, data: { uploaded: [], failed: [] } })
};

/**
 * Mock router for navigation
 */
export const mockRouter = {
	goto: vi.fn().mockResolvedValue(undefined),
	replace: vi.fn().mockResolvedValue(undefined),
	push: vi.fn().mockResolvedValue(undefined),
	back: vi.fn()
};

/**
 * Mock page store
 */
export const mockPageStore = {
	subscribe: vi.fn((callback) => {
		callback({
			url: new URL('http://localhost:3000/test'),
			params: {},
			route: { id: '/test' },
			status: 200,
			error: null
		});
		return { unsubscribe: vi.fn() };
	})
};

/**
 * Create a mock store with Svelte store interface
 */
export function createMockStore<T>(initialValue: T) {
	let value = initialValue;
	const subscribers = new Set<(value: T) => void>();

	return {
		subscribe: vi.fn((callback: (value: T) => void) => {
			subscribers.add(callback);
			callback(value);
			return {
				unsubscribe: () => subscribers.delete(callback)
			};
		}),
		set: vi.fn((newValue: T) => {
			value = newValue;
			subscribers.forEach(cb => { cb(value); });
		}),
		update: vi.fn((updater: (value: T) => T) => {
			value = updater(value);
			subscribers.forEach(cb => { cb(value); });
		}),
		// For testing - get current value
		get: () => value
	};
}

/**
 * Mock fetch with configurable responses
 */
export function createMockFetch(responses: Record<string, unknown> = {}) {
	return vi.fn(async (url: string, options?: RequestInit) => {
		const path = new URL(url).pathname;
		const response = responses[path] || { success: true, data: {} };

		return {
			ok: true,
			status: 200,
			statusText: 'OK',
			headers: new Headers({ 'content-type': 'application/json' }),
			json: async () => response,
			text: async () => JSON.stringify(response),
			blob: async () => new Blob([JSON.stringify(response)]),
			arrayBuffer: async () => new ArrayBuffer(0),
			formData: async () => new FormData(),
			clone: () => ({}),
			redirected: false,
			type: 'basic' as ResponseType,
			url,
			body: null,
			bodyUsed: false
		} as Response;
	});
}

/**
 * Mock IntersectionObserver for lazy loading tests
 */
export class MockIntersectionObserver {
	constructor(
		public callback: IntersectionObserverCallback,
		public options?: IntersectionObserverInit
	) {}

	observe = vi.fn();
	unobserve = vi.fn();
	disconnect = vi.fn();
	takeRecords = vi.fn().mockReturnValue([]);

	// Trigger intersection
	trigger(entries: Partial<IntersectionObserverEntry>[]): void {
		const fullEntries = entries.map(entry => ({
			boundingClientRect: {} as DOMRectReadOnly,
			intersectionRatio: 1,
			intersectionRect: {} as DOMRectReadOnly,
			isIntersecting: true,
			rootBounds: null,
			target: document.createElement('div'),
			time: Date.now(),
			...entry
		})) as IntersectionObserverEntry[];

		this.callback(fullEntries, this as unknown as IntersectionObserver);
	}
}

/**
 * Mock ResizeObserver for responsive component tests
 */
export class MockResizeObserver {
	constructor(public callback: ResizeObserverCallback) {}

	observe = vi.fn();
	unobserve = vi.fn();
	disconnect = vi.fn();

	// Trigger resize
	trigger(entries: Partial<ResizeObserverEntry>[]): void {
		const fullEntries = entries.map(entry => ({
			borderBoxSize: [{ blockSize: 100, inlineSize: 100 }],
			contentBoxSize: [{ blockSize: 100, inlineSize: 100 }],
			contentRect: {} as DOMRectReadOnly,
			devicePixelContentBoxSize: [],
			target: document.createElement('div'),
			...entry
		})) as ResizeObserverEntry[];

		this.callback(fullEntries, this as unknown as ResizeObserver);
	}
}

/**
 * Mock file operations
 */
export const mockFileReader = {
	readAsDataURL: vi.fn(),
	readAsText: vi.fn(),
	readAsArrayBuffer: vi.fn(),
	result: 'data:image/jpeg;base64,/9j/4AAQ...',
	addEventListener: vi.fn((event: string, callback: () => void) => {
		if (event === 'load') {
			setTimeout(callback, 0);
		}
	})
};

/**
 * Mock drag and drop event
 */
export function createDragEvent(
	type: string,
	files: File[] = []
): DragEvent {
	const dataTransfer = {
		files,
		items: files.map(file => ({
			kind: 'file',
			type: file.type,
			getAsFile: () => file
		})),
		types: ['Files'],
		getData: vi.fn(),
		setData: vi.fn(),
		clearData: vi.fn(),
		effectAllowed: 'all' as DataTransferEffectAllowed,
		dropEffect: 'copy' as DataTransferDropEffect
	};

	const event = new Event(type, {
		bubbles: true,
		cancelable: true
	}) as unknown as DragEvent;

	// Properly attach dataTransfer to the event
	Object.defineProperty(event, 'dataTransfer', {
		value: dataTransfer,
		writable: true,
		enumerable: true,
		configurable: true
	});

	return event;
}

/**
 * Mock localStorage
 */
export const mockLocalStorage = {
	getItem: vi.fn(),
	setItem: vi.fn(),
	removeItem: vi.fn(),
	clear: vi.fn(),
	length: 0,
	key: vi.fn()
};

/**
 * Mock WebSocket for real-time features
 */
export class MockWebSocket {
	url: string;
	readyState: number = WebSocket.CONNECTING;
	onopen: ((event: Event) => void) | null = null;
	onmessage: ((event: MessageEvent) => void) | null = null;
	onerror: ((event: Event) => void) | null = null;
	onclose: ((event: CloseEvent) => void) | null = null;

	constructor(url: string) {
		this.url = url;
		setTimeout(() => { this.connect(); }, 0);
	}

	connect(): void {
		this.readyState = WebSocket.OPEN;
		if (this.onopen) {
			this.onopen(new Event('open'));
		}
	}

	send = vi.fn();
	close = vi.fn(() => {
		this.readyState = WebSocket.CLOSED;
		if (this.onclose) {
			this.onclose(new CloseEvent('close'));
		}
	});

	// Test helper to simulate incoming messages
	receiveMessage(data: unknown): void {
		if (this.onmessage) {
			this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
		}
	}
}

/**
 * Mock timers utilities
 */
export const mockTimers = {
	setup: () => {
		vi.useFakeTimers();
	},
	cleanup: () => {
		vi.useRealTimers();
	},
	advance: (ms: number) => {
		vi.advanceTimersByTime(ms);
	},
	runAll: () => {
		vi.runAllTimers();
	}
};