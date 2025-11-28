/**
 * Tests for URL State Management Utilities
 *
 * Tests the URL-driven state management pattern with Svelte 5 runes.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { Page } from '@sveltejs/kit';
import {
	useUrlParam,
	useUrlParamNumber,
	useUrlParamBoolean,
	useUrlParamEnum,
	useUrlParamNullable,
	buildUrlParams,
	updateUrlParams,
	updateUrlParam
} from './urlState.svelte';
import { goto } from '$app/navigation';

/**
 * Helper function to create a mock Page object
 */
function createMockPage(searchParams: Record<string, string> = {}): Page {
	const url = new URL('http://localhost/test');
	for (const [key, value] of Object.entries(searchParams)) {
		url.searchParams.set(key, value);
	}

	return {
		url: url as any,
		params: {},
		route: { id: null },
		status: 200,
		error: null,
		data: {},
		state: {},
		form: undefined
	};
}

describe('useUrlParam', () => {
	it('should return default value when parameter is missing', () => {
		const page = createMockPage();
		const value = useUrlParam(page, 'query', 'default');
		expect(value).toBe('default');
	});

	it('should return URL parameter value when present', () => {
		const page = createMockPage({ query: 'test' });
		const value = useUrlParam(page, 'query', 'default');
		expect(value).toBe('test');
	});

	it('should use custom parser when provided', () => {
		const page = createMockPage({ ids: '1,2,3' });
		const parser = (val: string): number[] | null => {
			const parts = val.split(',').map(Number);
			return parts.every((n) => !isNaN(n)) ? parts : null;
		};
		const value = useUrlParam(page, 'ids', [] as number[], parser);
		expect(value).toEqual([1, 2, 3]);
	});

	it('should return default value when parser returns null', () => {
		const page = createMockPage({ ids: 'invalid' });
		const parser = (val: string): number[] | null => {
			const parts = val.split(',').map(Number);
			return parts.every((n) => !isNaN(n)) ? parts : null;
		};
		const value = useUrlParam(page, 'ids', [] as number[], parser);
		expect(value).toEqual([]);
	});

	it('should use custom validator when provided', () => {
		const page = createMockPage({ rating: '5' });
		const parser = (val: string) => parseInt(val, 10);
		const validator = (val: number) => (val >= 1 && val <= 5 ? val : null);
		const value = useUrlParam(page, 'rating', 3, parser, validator);
		expect(value).toBe(5);
	});

	it('should return default value when validator fails', () => {
		const page = createMockPage({ rating: '10' });
		const parser = (val: string) => parseInt(val, 10);
		const validator = (val: number) => (val >= 1 && val <= 5 ? val : null);
		const value = useUrlParam(page, 'rating', 3, parser, validator);
		expect(value).toBe(3);
	});
});

describe('useUrlParamNumber', () => {
	it('should parse integer from URL', () => {
		const page = createMockPage({ page: '2' });
		const value = useUrlParamNumber(page, 'page', 1);
		expect(value).toBe(2);
	});

	it('should return default for invalid number', () => {
		const page = createMockPage({ page: 'invalid' });
		const value = useUrlParamNumber(page, 'page', 1);
		expect(value).toBe(1);
	});

	it('should enforce minimum constraint', () => {
		const page = createMockPage({ page: '0' });
		const value = useUrlParamNumber(page, 'page', 1, { min: 1 });
		expect(value).toBe(1);
	});

	it('should enforce maximum constraint', () => {
		const page = createMockPage({ page: '1000' });
		const value = useUrlParamNumber(page, 'page', 1, { max: 999 });
		expect(value).toBe(1);
	});

	it('should allow values within min/max range', () => {
		const page = createMockPage({ page: '50' });
		const value = useUrlParamNumber(page, 'page', 1, { min: 1, max: 100 });
		expect(value).toBe(50);
	});

	it('should parse float when allowDecimals is true', () => {
		const page = createMockPage({ threshold: '0.75' });
		const value = useUrlParamNumber(page, 'threshold', 0.5, { allowDecimals: true });
		expect(value).toBe(0.75);
	});

	it('should enforce min/max for decimal values', () => {
		const page = createMockPage({ threshold: '1.5' });
		const value = useUrlParamNumber(page, 'threshold', 0.5, {
			min: 0.0,
			max: 1.0,
			allowDecimals: true
		});
		expect(value).toBe(0.5);
	});

	it('should parse integer even with decimal point when allowDecimals is false', () => {
		const page = createMockPage({ page: '2.7' });
		const value = useUrlParamNumber(page, 'page', 1, { allowDecimals: false });
		expect(value).toBe(2); // parseInt truncates
	});
});

describe('useUrlParamBoolean', () => {
	it('should parse "true" as true', () => {
		const page = createMockPage({ enabled: 'true' });
		const value = useUrlParamBoolean(page, 'enabled', false);
		expect(value).toBe(true);
	});

	it('should parse "false" as false', () => {
		const page = createMockPage({ enabled: 'false' });
		const value = useUrlParamBoolean(page, 'enabled', true);
		expect(value).toBe(false);
	});

	it('should parse "1" as true', () => {
		const page = createMockPage({ enabled: '1' });
		const value = useUrlParamBoolean(page, 'enabled', false);
		expect(value).toBe(true);
	});

	it('should parse "0" as false', () => {
		const page = createMockPage({ enabled: '0' });
		const value = useUrlParamBoolean(page, 'enabled', true);
		expect(value).toBe(false);
	});

	it('should parse "yes" as true (case-insensitive)', () => {
		const page = createMockPage({ enabled: 'YES' });
		const value = useUrlParamBoolean(page, 'enabled', false);
		expect(value).toBe(true);
	});

	it('should parse "no" as false (case-insensitive)', () => {
		const page = createMockPage({ enabled: 'NO' });
		const value = useUrlParamBoolean(page, 'enabled', true);
		expect(value).toBe(false);
	});

	it('should return default for invalid boolean string', () => {
		const page = createMockPage({ enabled: 'maybe' });
		const value = useUrlParamBoolean(page, 'enabled', false);
		expect(value).toBe(false);
	});

	it('should return default when parameter is missing', () => {
		const page = createMockPage();
		const value = useUrlParamBoolean(page, 'enabled', true);
		expect(value).toBe(true);
	});
});

describe('useUrlParamEnum', () => {
	type SortBy = 'name' | 'date' | 'size';
	const allowedValues: readonly SortBy[] = ['name', 'date', 'size'];

	it('should return valid enum value', () => {
		const page = createMockPage({ sort: 'date' });
		const value = useUrlParamEnum<SortBy>(page, 'sort', 'name', allowedValues);
		expect(value).toBe('date');
	});

	it('should return default for invalid enum value', () => {
		const page = createMockPage({ sort: 'invalid' });
		const value = useUrlParamEnum<SortBy>(page, 'sort', 'name', allowedValues);
		expect(value).toBe('name');
	});

	it('should return default when parameter is missing', () => {
		const page = createMockPage();
		const value = useUrlParamEnum<SortBy>(page, 'sort', 'name', allowedValues);
		expect(value).toBe('name');
	});

	it('should be case-sensitive', () => {
		const page = createMockPage({ sort: 'Date' });
		const value = useUrlParamEnum<SortBy>(page, 'sort', 'name', allowedValues);
		expect(value).toBe('name'); // 'Date' !== 'date'
	});
});

describe('useUrlParamNullable', () => {
	it('should return null when parameter is missing', () => {
		const page = createMockPage();
		const value = useUrlParamNullable(page, 'connector_id');
		expect(value).toBeNull();
	});

	it('should return string value when parameter is present', () => {
		const page = createMockPage({ connector_id: 'abc-123' });
		const value = useUrlParamNullable(page, 'connector_id');
		expect(value).toBe('abc-123');
	});

	it('should return empty string when parameter is empty', () => {
		const page = createMockPage({ connector_id: '' });
		const value = useUrlParamNullable(page, 'connector_id');
		expect(value).toBe('');
	});
});

describe('buildUrlParams', () => {
	it('should include all parameters when no defaults', () => {
		const params = buildUrlParams({ page: 1, query: 'test' });
		expect(params.get('page')).toBe('1');
		expect(params.get('query')).toBe('test');
	});

	it('should omit parameters that match defaults', () => {
		const params = buildUrlParams(
			{ page: 1, perPage: 24, query: 'test' },
			{ page: 1, perPage: 24 }
		);
		expect(params.get('page')).toBeNull();
		expect(params.get('perPage')).toBeNull();
		expect(params.get('query')).toBe('test');
	});

	it('should omit null and undefined values', () => {
		const params = buildUrlParams({ page: 1, query: null, filter: undefined });
		expect(params.get('page')).toBe('1');
		expect(params.get('query')).toBeNull();
		expect(params.get('filter')).toBeNull();
	});

	it('should convert numbers and booleans to strings', () => {
		const params = buildUrlParams({ page: 42, enabled: true });
		expect(params.get('page')).toBe('42');
		expect(params.get('enabled')).toBe('true');
	});

	it('should handle empty object', () => {
		const params = buildUrlParams({});
		expect(params.toString()).toBe('');
	});
});

describe('updateUrlParams', () => {
	let gotoMock: any;

	beforeEach(() => {
		gotoMock = vi.mocked(goto);
		gotoMock.mockClear();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('should update single parameter', () => {
		const currentParams = new URLSearchParams('?page=1&query=test');
		updateUrlParams({ page: 2 }, currentParams);

		expect(gotoMock).toHaveBeenCalledWith(
			expect.stringContaining('page=2'),
			expect.objectContaining({ replaceState: true, keepFocus: true })
		);
		expect(gotoMock).toHaveBeenCalledWith(
			expect.stringContaining('query=test'),
			expect.any(Object)
		);
	});

	it('should add new parameter', () => {
		const currentParams = new URLSearchParams('?page=1');
		updateUrlParams({ query: 'beach' }, currentParams);

		expect(gotoMock).toHaveBeenCalledWith(
			expect.stringContaining('query=beach'),
			expect.any(Object)
		);
	});

	it('should remove parameter when set to null', () => {
		const currentParams = new URLSearchParams('?page=1&query=test');
		updateUrlParams({ query: null }, currentParams);

		expect(gotoMock).toHaveBeenCalledWith(
			expect.not.stringContaining('query'),
			expect.any(Object)
		);
		expect(gotoMock).toHaveBeenCalledWith(
			expect.stringContaining('page=1'),
			expect.any(Object)
		);
	});

	it('should remove parameter when set to undefined', () => {
		const currentParams = new URLSearchParams('?page=1&query=test');
		updateUrlParams({ query: undefined }, currentParams);

		expect(gotoMock).toHaveBeenCalledWith(
			expect.not.stringContaining('query'),
			expect.any(Object)
		);
	});

	it('should update multiple parameters at once', () => {
		const currentParams = new URLSearchParams('?page=1');
		updateUrlParams({ page: 2, query: 'beach', sort: 'date' }, currentParams);

		expect(gotoMock).toHaveBeenCalledWith(
			expect.stringContaining('page=2'),
			expect.any(Object)
		);
		expect(gotoMock).toHaveBeenCalledWith(
			expect.stringContaining('query=beach'),
			expect.any(Object)
		);
		expect(gotoMock).toHaveBeenCalledWith(
			expect.stringContaining('sort=date'),
			expect.any(Object)
		);
	});

	it('should convert numbers to strings', () => {
		const currentParams = new URLSearchParams();
		updateUrlParams({ page: 42 }, currentParams);

		expect(gotoMock).toHaveBeenCalledWith(
			expect.stringContaining('page=42'),
			expect.any(Object)
		);
	});

	it('should convert booleans to strings', () => {
		const currentParams = new URLSearchParams();
		updateUrlParams({ enabled: true }, currentParams);

		expect(gotoMock).toHaveBeenCalledWith(
			expect.stringContaining('enabled=true'),
			expect.any(Object)
		);
	});

	it('should use custom options', () => {
		const currentParams = new URLSearchParams();
		updateUrlParams(
			{ page: 2 },
			currentParams,
			{ replaceState: false, keepFocus: false }
		);

		expect(gotoMock).toHaveBeenCalledWith(
			expect.any(String),
			expect.objectContaining({ replaceState: false, keepFocus: false })
		);
	});

	it('should use custom basePath', () => {
		const currentParams = new URLSearchParams();
		updateUrlParams({ page: 2 }, currentParams, { basePath: '/search' });

		expect(gotoMock).toHaveBeenCalledWith(
			expect.stringContaining('/search?page=2'),
			expect.any(Object)
		);
	});

	it('should navigate to path without query string when no params', () => {
		const currentParams = new URLSearchParams('?page=1');
		updateUrlParams({ page: null }, currentParams, { basePath: '/photos' });

		expect(gotoMock).toHaveBeenCalledWith(
			'/photos',
			expect.any(Object)
		);
	});
});

describe('updateUrlParam', () => {
	let gotoMock: any;

	beforeEach(() => {
		gotoMock = vi.mocked(goto);
		gotoMock.mockClear();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('should update single parameter', () => {
		const currentParams = new URLSearchParams('?page=1');
		updateUrlParam('page', 2, currentParams);

		expect(gotoMock).toHaveBeenCalledWith(
			expect.stringContaining('page=2'),
			expect.any(Object)
		);
	});

	it('should remove parameter when set to null', () => {
		const currentParams = new URLSearchParams('?page=1&query=test');
		updateUrlParam('query', null, currentParams);

		expect(gotoMock).toHaveBeenCalledWith(
			expect.not.stringContaining('query'),
			expect.any(Object)
		);
	});
});

describe('integration scenarios', () => {
	it('should handle search page scenario', () => {
		const page = createMockPage({
			q: 'beach sunset',
			page: '2',
			per_page: '48',
			similarity_threshold: '0.25'
		});

		const query = useUrlParam(page, 'q', '');
		const currentPage = useUrlParamNumber(page, 'page', 1, { min: 1 });
		const perPage = useUrlParamNumber(page, 'per_page', 24, { min: 1, max: 100 });
		const threshold = useUrlParamNumber(page, 'similarity_threshold', 0.18, {
			min: 0.0,
			max: 1.0,
			allowDecimals: true
		});

		expect(query).toBe('beach sunset');
		expect(currentPage).toBe(2);
		expect(perPage).toBe(48);
		expect(threshold).toBe(0.25);
	});

	it('should handle faces page scenario', () => {
		const page = createMockPage({
			view: 'graph',
			page: '1',
			named: 'true',
			sort_by: 'face_count'
		});

		type ViewType = 'list' | 'graph';
		const view = useUrlParamEnum<ViewType>(page, 'view', 'list', ['list', 'graph']);
		const currentPage = useUrlParamNumber(page, 'page', 1, { min: 1 });
		const named = useUrlParamBoolean(page, 'named', false);

		type SortBy = 'face_count' | 'photo_count' | 'name';
		const sortBy = useUrlParamEnum<SortBy>(
			page,
			'sort_by',
			'face_count',
			['face_count', 'photo_count', 'name']
		);

		expect(view).toBe('graph');
		expect(currentPage).toBe(1);
		expect(named).toBe(true);
		expect(sortBy).toBe('face_count');
	});

	it('should handle optional filter IDs', () => {
		const page = createMockPage({
			connector_id: 'abc-123',
			album_id: 'def-456'
		});

		const connectorId = useUrlParamNullable(page, 'connector_id');
		const albumId = useUrlParamNullable(page, 'album_id');

		expect(connectorId).toBe('abc-123');
		expect(albumId).toBe('def-456');
	});

	it('should handle missing optional filter IDs', () => {
		const page = createMockPage();

		const connectorId = useUrlParamNullable(page, 'connector_id');
		const albumId = useUrlParamNullable(page, 'album_id');

		expect(connectorId).toBeNull();
		expect(albumId).toBeNull();
	});
});
