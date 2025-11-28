// API client for Photo Explorer backend

import { API_DEFAULT_TIMEOUT } from '$lib/constants';
import { z } from 'zod';

/** Base API host URL - export for use in components that need direct URLs (images, etc.) */
export const API_HOST = (import.meta.env['PUBLIC_API_URL'] !== undefined && import.meta.env['PUBLIC_API_URL'] !== null && import.meta.env['PUBLIC_API_URL'] !== '') ? String(import.meta.env['PUBLIC_API_URL']) : 'http://localhost:8000';
const API_BASE = `${API_HOST}/api/v1`;

/**
 * Schema for API error responses
 */
const ApiErrorSchema = z.object({
	code: z.string(),
	message: z.string(),
	details: z.record(z.string(), z.unknown()).optional()
});

/**
 * Schema for API pagination metadata
 */
const ApiMetaSchema = z.object({
	page: z.number().optional(),
	per_page: z.number().optional(),
	total: z.number().optional()
});

/**
 * Generic API response wrapper schema
 * This validates the outer envelope of all API responses
 */
function createApiResponseSchema<T extends z.ZodTypeAny>(dataSchema: T): z.ZodObject<{
	success: z.ZodBoolean;
	data: T;
	error: z.ZodOptional<typeof ApiErrorSchema>;
	meta: z.ZodOptional<typeof ApiMetaSchema>;
}> {
	return z.object({
		success: z.boolean(),
		data: dataSchema,
		error: ApiErrorSchema.optional(),
		meta: ApiMetaSchema.optional()
	});
}

/**
 * Type-safe API response wrapper
 */
interface ApiResponse<T> {
	success: boolean;
	data: T;
	error?: {
		code: string;
		message: string;
		details?: Record<string, unknown> | undefined;
	} | undefined;
	meta?: {
		page?: number | undefined;
		per_page?: number | undefined;
		total?: number | undefined;
	} | undefined;
}

class ApiError extends Error {
	code: string;
	details?: Record<string, unknown> | undefined;

	constructor(message: string, code: string, details?: Record<string, unknown>) {
		super(message);
		this.name = 'ApiError';
		this.code = code;
		this.details = details;
	}
}

/**
 * Creates a fetch request with timeout support and optional external abort signal
 */
async function fetchWithTimeout(
	url: string,
	options?: RequestInit,
	timeout: number = API_DEFAULT_TIMEOUT
): Promise<Response> {
	const controller = new AbortController();
	const timeoutId = setTimeout(() => { controller.abort(); }, timeout);

	// If external signal provided, listen to it and abort our controller
	const externalSignal = options?.signal;
	const abortHandler = (): void => { controller.abort(); };
	if (externalSignal) {
		externalSignal.addEventListener('abort', abortHandler);
	}

	try {
		const response = await fetch(url, {
			...options,
			signal: controller.signal
		});
		return response;
	} catch (error) {
		if (error instanceof Error && error.name === 'AbortError') {
			// Check if it was external abort or timeout
			if (externalSignal?.aborted) {
				// Re-throw to be handled by caller
				throw error;
			}
			throw new ApiError(
				'Request timeout - the server took too long to respond',
				'TIMEOUT_ERROR'
			);
		}
		throw error;
	} finally {
		clearTimeout(timeoutId);
		if (externalSignal) {
			externalSignal.removeEventListener('abort', abortHandler);
		}
	}
}

/**
 * Handles API response with comprehensive error handling and optional runtime validation
 * @param response - The fetch Response object
 * @param schema - Optional Zod schema to validate the response data
 * @returns Validated or unvalidated API response
 */
async function handleResponse<T>(
	response: Response,
	schema?: z.ZodType<T>
): Promise<ApiResponse<T>> {
	// Check content type before parsing
	const contentType = response.headers.get('content-type');
	const isJson = contentType?.includes('application/json');

	let rawData: unknown;
	try {
		if (isJson) {
			rawData = await response.json() as unknown;
		} else {
			// Non-JSON response (e.g., HTML error page)
			const text = await response.text();
			throw new ApiError(
				`Server returned non-JSON response: ${response.statusText}`,
				'INVALID_RESPONSE',
				{ statusCode: response.status, body: text.substring(0, 200) }
			);
		}
	} catch (error) {
		// Failed to parse JSON or read response body
		if (error instanceof ApiError) {
			throw error;
		}
		throw new ApiError(
			'Failed to parse server response',
			'PARSE_ERROR',
			{ originalError: error instanceof Error ? error.message : String(error) }
		);
	}

	// If schema provided, validate the response
	if (schema) {
		const responseSchema = createApiResponseSchema(schema);
		const parseResult = responseSchema.safeParse(rawData);

		if (!parseResult.success) {
			throw new ApiError(
				'Server response does not match expected schema',
				'VALIDATION_ERROR',
				{
					zodErrors: parseResult.error.format(),
					receivedData: rawData
				}
			);
		}

		const data = parseResult.data;

		if (!response.ok || !data.success) {
			throw new ApiError(
				data.error?.message ?? 'Request failed',
				data.error?.code ?? 'UNKNOWN_ERROR',
				data.error?.details
			);
		}

		return data;
	}

	// Legacy path: No validation, assumes data structure is correct
	// TODO: Migrate all call sites to use Zod schemas
	const data = rawData as ApiResponse<T>;

	if (!response.ok || !data.success) {
		throw new ApiError(
			data.error?.message ?? 'Request failed',
			data.error?.code ?? 'UNKNOWN_ERROR',
			data.error?.details
		);
	}

	// Return with explicit optional properties set to undefined if missing
	return {
		success: data.success,
		data: data.data,
		error: data.error,
		meta: data.meta
	};
}

/**
 * Type-safe API client with optional runtime validation
 *
 * Schemas are optional for backward compatibility, but strongly recommended.
 * New code should always provide Zod schemas for runtime type safety.
 */
export const client = {
	/**
	 * GET request with optional runtime validation
	 * @example
	 * // With validation (type-safe)
	 * const response = await client.get('/photos', PhotoSchema, { params: { page: '1' } });
	 *
	 * // Without validation (legacy, less safe)
	 * const response = await client.get<Photo[]>('/photos', { params: { page: '1' } });
	 */
	async get<T>(
		path: string,
		schemaOrOptions?: z.ZodType<T> | { params?: Record<string, string>; signal?: AbortSignal },
		options?: { params?: Record<string, string>; signal?: AbortSignal }
	): Promise<ApiResponse<T>> {
		// Determine if first arg is schema or options
		const isSchema = schemaOrOptions && 'parse' in schemaOrOptions;
		const schema = isSchema ? schemaOrOptions : undefined;
		const opts = isSchema ? options : schemaOrOptions as { params?: Record<string, string>; signal?: AbortSignal } | undefined;
		try {
			const url = new URL(`${API_BASE}${path}`);
			if (opts?.params) {
				Object.entries(opts.params).forEach(([key, value]) => {
					url.searchParams.set(key, value);
				});
			}

			const response = await fetchWithTimeout(
				url.toString(),
				opts?.signal ? { signal: opts.signal } : {}
			);
			return handleResponse<T>(response, schema);
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			// Network error (no connection, CORS, DNS failure, etc.)
			throw new ApiError(
				'Network error - unable to connect to server. Please check your connection.',
				'NETWORK_ERROR',
				{ originalError: error instanceof Error ? error.message : String(error) }
			);
		}
	},

	/**
	 * POST request with optional runtime validation
	 * @example
	 * // With validation (type-safe)
	 * const response = await client.post('/photos', PhotoSchema, { name: 'photo.jpg' });
	 *
	 * // Without validation (legacy, less safe)
	 * const response = await client.post<Photo>('/photos', { name: 'photo.jpg' });
	 */
	async post<T>(path: string, schemaOrBody?: z.ZodType<T> | Record<string, unknown>, body?: unknown): Promise<ApiResponse<T>> {
		// Determine if first arg is schema or body
		const isSchema = schemaOrBody !== undefined && 'parse' in schemaOrBody;
		const schema = isSchema ? (schemaOrBody as z.ZodType<T>) : undefined;
		const requestBody = isSchema ? body : schemaOrBody;
		try {
			const response = await fetchWithTimeout(`${API_BASE}${path}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: requestBody !== undefined && requestBody !== null ? JSON.stringify(requestBody) : null
			});
			return handleResponse<T>(response, schema);
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			throw new ApiError(
				'Network error - unable to connect to server. Please check your connection.',
				'NETWORK_ERROR',
				{ originalError: error instanceof Error ? error.message : String(error) }
			);
		}
	},

	/**
	 * POST form data with optional runtime validation
	 */
	async postForm<T>(path: string, schemaOrFormData: z.ZodType<T> | FormData, formData?: FormData): Promise<ApiResponse<T>> {
		// Determine if first arg is schema or form data
		const isSchema = 'parse' in schemaOrFormData;
		const schema = isSchema ? schemaOrFormData : undefined;
		const data = isSchema ? formData : schemaOrFormData;

		if (!data) {
			throw new ApiError(
				'FormData is required for postForm',
				'INVALID_ARGUMENT'
			);
		}

		try {
			const response = await fetchWithTimeout(`${API_BASE}${path}`, {
				method: 'POST',
				body: data
			});
			return handleResponse<T>(response, schema);
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			throw new ApiError(
				'Network error - unable to connect to server. Please check your connection.',
				'NETWORK_ERROR',
				{ originalError: error instanceof Error ? error.message : String(error) }
			);
		}
	},

	/**
	 * PATCH request with optional runtime validation
	 */
	async patch<T>(path: string, schemaOrBody?: z.ZodType<T> | Record<string, unknown>, body?: unknown): Promise<ApiResponse<T>> {
		// Determine if first arg is schema or body
		const isSchema = schemaOrBody !== undefined && 'parse' in schemaOrBody;
		const schema = isSchema ? (schemaOrBody as z.ZodType<T>) : undefined;
		const requestBody = isSchema ? body : schemaOrBody;
		try {
			const response = await fetchWithTimeout(`${API_BASE}${path}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(requestBody)
			});
			return handleResponse<T>(response, schema);
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			throw new ApiError(
				'Network error - unable to connect to server. Please check your connection.',
				'NETWORK_ERROR',
				{ originalError: error instanceof Error ? error.message : String(error) }
			);
		}
	},

	/**
	 * DELETE request with optional runtime validation
	 */
	async delete<T>(path: string, schema?: z.ZodType<T>): Promise<ApiResponse<T>> {
		try {
			const response = await fetchWithTimeout(`${API_BASE}${path}`, {
				method: 'DELETE'
			});
			return handleResponse<T>(response, schema);
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			throw new ApiError(
				'Network error - unable to connect to server. Please check your connection.',
				'NETWORK_ERROR',
				{ originalError: error instanceof Error ? error.message : String(error) }
			);
		}
	}
};

export { ApiError };
