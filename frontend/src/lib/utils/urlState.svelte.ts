/**
 * URL State Management Utilities for Svelte 5
 *
 * Provides reusable utilities for URL-driven state management using the
 * "URL as single source of truth" pattern. Functions parse URL parameters
 * and should be used within $derived contexts in components for reactivity.
 *
 * @example
 * ```typescript
 * // In a component
 * import { page } from '$app/stores';
 * import { useUrlParam, useUrlParamNumber, updateUrlParam } from '$lib/utils/urlState.svelte';
 *
 * const query = $derived(useUrlParam($page, 'q', ''));
 * const currentPage = $derived(useUrlParamNumber($page, 'page', 1, { min: 1 }));
 * const enabled = $derived(useUrlParamBoolean($page, 'enabled', false));
 *
 * // Update a single parameter
 * updateUrlParam('page', 2, $page.url.searchParams);
 * ```
 */

import { goto } from '$app/navigation';
import type { Page } from '@sveltejs/kit';

/**
 * Parser function type - converts string to desired type T
 */
type Parser<T> = (value: string) => T | null;

/**
 * Validator function type - validates and potentially transforms a value
 */
type Validator<T> = (value: T) => T | null;

/**
 * Options for number parameter parsing
 */
export interface NumberOptions {
	/** Minimum allowed value (inclusive) */
	min?: number;
	/** Maximum allowed value (inclusive) */
	max?: number;
	/** Whether to allow decimal values (default: false) */
	allowDecimals?: boolean;
}

/**
 * Core utility: Extract a URL parameter with type safety and validation
 *
 * Parses URL parameters with custom logic. This function should be called
 * within a $derived context in components.
 *
 * @param page - The SvelteKit page store
 * @param key - URL parameter key to read
 * @param defaultValue - Default value if parameter is missing or invalid
 * @param parser - Optional parser function to convert string to type T
 * @param validator - Optional validator function to validate/transform value
 * @returns Parsed and validated value
 *
 * @example
 * ```typescript
 * // In a component
 * const sortBy = $derived(useUrlParam($page, 'sort', 'name' as const, undefined, (val) => {
 *   return ['name', 'date', 'size'].includes(val) ? val : null;
 * }));
 * ```
 */
export function useUrlParam<T>(
	page: Page,
	key: string,
	defaultValue: T,
	parser?: Parser<T>,
	validator?: Validator<T>
): T {
	const urlValue = page.url.searchParams.get(key);

	if (urlValue === null) {
		return defaultValue;
	}

	// If parser provided, use it
	let parsed: T | null = null;
	if (parser) {
		parsed = parser(urlValue);
	} else {
		// Default: treat as string (cast to T)
		parsed = urlValue as unknown as T;
	}

	if (parsed === null) {
		return defaultValue;
	}

	// If validator provided, use it
	if (validator) {
		const validated = validator(parsed);
		return validated ?? defaultValue;
	}

	return parsed;
}

/**
 * Extract a number URL parameter with validation
 *
 * Parses the URL parameter as an integer or float, with optional min/max constraints.
 *
 * @param page - The SvelteKit page store
 * @param key - URL parameter key to read
 * @param defaultValue - Default value if parameter is missing or invalid
 * @param options - Number parsing options (min, max, allowDecimals)
 * @returns Reactive derived number value
 *
 * @example
 * ```typescript
 * const page = useUrlParamNumber($page, 'page', 1, { min: 1, max: 999 });
 * const threshold = useUrlParamNumber($page, 'threshold', 0.5, {
 *   min: 0.0,
 *   max: 1.0,
 *   allowDecimals: true
 * });
 * ```
 */
export function useUrlParamNumber(
	page: Page,
	key: string,
	defaultValue: number,
	options: NumberOptions = {}
): number {
	const { min, max, allowDecimals = false } = options;

	const parser: Parser<number> = (value: string) => {
		const parsed = allowDecimals ? parseFloat(value) : parseInt(value, 10);
		return isNaN(parsed) ? null : parsed;
	};

	const validator: Validator<number> = (value: number) => {
		if (min !== undefined && value < min) {
			return null;
		}
		if (max !== undefined && value > max) {
			return null;
		}
		return value;
	};

	return useUrlParam(page, key, defaultValue, parser, validator);
}

/**
 * Extract a boolean URL parameter
 *
 * Parses common boolean representations: 'true', '1', 'yes' = true
 *
 * @param page - The SvelteKit page store
 * @param key - URL parameter key to read
 * @param defaultValue - Default value if parameter is missing or invalid
 * @returns Reactive derived boolean value
 *
 * @example
 * ```typescript
 * const showNamed = useUrlParamBoolean($page, 'named', false);
 * const editMode = useUrlParamBoolean($page, 'edit', false);
 * ```
 */
export function useUrlParamBoolean(
	page: Page,
	key: string,
	defaultValue: boolean
): boolean {
	const parser: Parser<boolean> = (value: string) => {
		const lower = value.toLowerCase();
		if (lower === 'true' || lower === '1' || lower === 'yes') {
			return true;
		}
		if (lower === 'false' || lower === '0' || lower === 'no') {
			return false;
		}
		return null;
	};

	return useUrlParam(page, key, defaultValue, parser);
}

/**
 * Extract an enum URL parameter with type safety
 *
 * Ensures the URL parameter matches one of the allowed values.
 *
 * @param page - The SvelteKit page store
 * @param key - URL parameter key to read
 * @param defaultValue - Default value if parameter is missing or invalid
 * @param allowedValues - Array of allowed enum values
 * @returns Reactive derived enum value
 *
 * @example
 * ```typescript
 * type SortBy = 'name' | 'date' | 'size';
 * const sortBy = useUrlParamEnum<SortBy>(
 *   $page,
 *   'sort',
 *   'name',
 *   ['name', 'date', 'size']
 * );
 * ```
 */
export function useUrlParamEnum<T extends string>(
	page: Page,
	key: string,
	defaultValue: T,
	allowedValues: readonly T[]
): T {
	const validator: Validator<T> = (value: T) => {
		return allowedValues.includes(value) ? value : null;
	};

	return useUrlParam(
		page,
		key,
		defaultValue,
		(val) => val as T,
		validator
	);
}

/**
 * Extract a nullable string URL parameter
 *
 * Returns null if parameter is missing, otherwise returns the string value.
 * Useful for optional filters or IDs.
 *
 * @param page - The SvelteKit page store
 * @param key - URL parameter key to read
 * @returns Nullable string value
 *
 * @example
 * ```typescript
 * // In a component
 * const connectorId = $derived(useUrlParamNullable($page, 'connector_id'));
 * const albumId = $derived(useUrlParamNullable($page, 'album_id'));
 * ```
 */
export function useUrlParamNullable(
	page: Page,
	key: string
): string | null {
	return page.url.searchParams.get(key);
}

/**
 * Options for updateUrlParams function
 */
export interface UpdateUrlOptions {
	/** Whether to replace browser history entry (default: true) */
	replaceState?: boolean;
	/** Whether to keep focus on current element (default: true) */
	keepFocus?: boolean;
	/** Optional base path (default: current path) */
	basePath?: string;
}

/**
 * Update one or more URL parameters
 *
 * Merges updates into the current URL search parameters and navigates
 * to the new URL. By default, uses replaceState to avoid polluting history.
 *
 * @param updates - Object with parameter key-value pairs to update
 * @param currentParams - Current URLSearchParams (from $page.url.searchParams)
 * @param options - Navigation options
 *
 * @example
 * ```typescript
 * // Update a single parameter
 * updateUrlParams({ page: 2 }, $page.url.searchParams);
 *
 * // Update multiple parameters
 * updateUrlParams(
 *   { query: 'beach', page: 1, sort: 'date' },
 *   $page.url.searchParams
 * );
 *
 * // Remove a parameter by setting to null
 * updateUrlParams({ filter: null }, $page.url.searchParams);
 * ```
 */
export function updateUrlParams(
	updates: Record<string, string | number | boolean | null | undefined>,
	currentParams: URLSearchParams,
	options: UpdateUrlOptions = {}
): void {
	const {
		replaceState = true,
		keepFocus = true,
		basePath
	} = options;

	const newParams = new URLSearchParams(currentParams);

	// Apply updates
	for (const [key, value] of Object.entries(updates)) {
		if (value === null || value === undefined) {
			// Remove parameter
			newParams.delete(key);
		} else {
			// Set parameter (convert to string)
			newParams.set(key, String(value));
		}
	}

	// Build new URL
	const path = basePath ?? window.location.pathname;
	const queryString = newParams.toString();
	const newUrl = queryString ? `${path}?${queryString}` : path;

	// Navigate
	void goto(newUrl, { replaceState, keepFocus });
}

/**
 * Update a single URL parameter (convenience wrapper)
 *
 * @param key - Parameter key to update
 * @param value - New value (null to remove)
 * @param currentParams - Current URLSearchParams (from $page.url.searchParams)
 * @param options - Navigation options
 *
 * @example
 * ```typescript
 * updateUrlParam('page', 2, $page.url.searchParams);
 * updateUrlParam('filter', null, $page.url.searchParams); // Remove parameter
 * ```
 */
export function updateUrlParam(
	key: string,
	value: string | number | boolean | null,
	currentParams: URLSearchParams,
	options?: UpdateUrlOptions
): void {
	updateUrlParams({ [key]: value }, currentParams, options);
}

/**
 * Build URL search params from an object, omitting default values
 *
 * Helper function to build URLSearchParams while excluding parameters
 * that match their default values. Useful for clean, shareable URLs.
 *
 * @param params - Parameter values to include
 * @param defaults - Default values to omit from URL
 * @returns URLSearchParams instance
 *
 * @example
 * ```typescript
 * const params = buildUrlParams(
 *   { page: 1, perPage: 24, sortBy: 'date' },
 *   { page: 1, perPage: 24, sortBy: 'name' }
 * );
 * // Result: only "sortBy=date" is included (others match defaults)
 * ```
 */
export function buildUrlParams<T extends Record<string, unknown>>(
	params: T,
	defaults: Partial<T> = {}
): URLSearchParams {
	const urlParams = new URLSearchParams();

	for (const [key, value] of Object.entries(params)) {
		// Skip null/undefined
		if (value === null || value === undefined) {
			continue;
		}

		// Skip if matches default
		if (key in defaults && defaults[key] === value) {
			continue;
		}

		// Add parameter
		urlParams.set(key, String(value));
	}

	return urlParams;
}

/**
 * Parse multiple URL parameters at once with type safety
 *
 * Returns an object with all requested parameters parsed according
 * to their specifications. Use within a $derived context.
 *
 * @param page - The SvelteKit page store
 * @param specs - Object mapping keys to parameter specifications
 * @returns Object with parsed parameter values
 *
 * @example
 * ```typescript
 * // In a component
 * const params = $derived(useUrlParams($page, {
 *   query: { type: 'string', default: '' },
 *   page: { type: 'number', default: 1, min: 1 },
 *   enabled: { type: 'boolean', default: false },
 *   sort: { type: 'enum', default: 'name', allowed: ['name', 'date'] }
 * }));
 * // Access: params.query, params.page, params.enabled, params.sort
 * ```
 */
export function useUrlParams<T extends Record<string, unknown>>(
	page: Page,
	specs: UrlParamSpecs<T>
): T {
	const result = {} as T;

	for (const [key, specAny] of Object.entries(specs)) {
		const spec = specAny as UrlParamSpec<T[keyof T]>;

		if (spec.type === 'string') {
			result[key as keyof T] = useUrlParam(
				page,
				key,
				spec.default
			);
		} else if (spec.type === 'number') {
			const numSpec = spec;
			result[key as keyof T] = useUrlParamNumber(
				page,
				key,
				numSpec.default as number,
				{ min: numSpec.min, max: numSpec.max }
			) as T[keyof T];
		} else if (spec.type === 'boolean') {
			result[key as keyof T] = useUrlParamBoolean(
				page,
				key,
				spec.default as boolean
			) as T[keyof T];
		} else {
			const enumSpec = spec;
			result[key as keyof T] = useUrlParamEnum(
				page,
				key,
				enumSpec.default as string,
				enumSpec.allowed as readonly string[]
			) as T[keyof T];
		}
	}

	return result;
}

/**
 * Type definitions for useUrlParams specifications
 */
type UrlParamSpecs<T extends Record<string, unknown>> = {
	[K in keyof T]: UrlParamSpec<T[K]>;
};

type UrlParamSpec<T> =
	| { type: 'string'; default: T }
	| { type: 'number'; default: T; min?: number; max?: number }
	| { type: 'boolean'; default: T }
	| { type: 'enum'; default: T; allowed: readonly (T extends string ? T : never)[] };
