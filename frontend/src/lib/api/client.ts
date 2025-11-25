// API client for Photo Explorer backend

/** Base API host URL - export for use in components that need direct URLs (images, etc.) */
export const API_HOST = import.meta.env['PUBLIC_API_URL'] || 'http://localhost:8000';
const API_BASE = `${API_HOST}/api/v1`;

/** Default request timeout in milliseconds */
const DEFAULT_TIMEOUT = 30000;

interface ApiResponse<T> {
	success: boolean;
	data: T;
	error?: {
		code: string;
		message: string;
		details?: Record<string, unknown>;
	};
	meta?: {
		page?: number;
		per_page?: number;
		total?: number;
	};
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
 * Creates a fetch request with timeout support
 */
async function fetchWithTimeout(
	url: string,
	options?: RequestInit,
	timeout = DEFAULT_TIMEOUT
): Promise<Response> {
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), timeout);

	try {
		const response = await fetch(url, {
			...options,
			signal: controller.signal
		});
		return response;
	} catch (error) {
		if (error instanceof Error && error.name === 'AbortError') {
			throw new ApiError(
				'Request timeout - the server took too long to respond',
				'TIMEOUT_ERROR'
			);
		}
		throw error;
	} finally {
		clearTimeout(timeoutId);
	}
}

/**
 * Handles API response with comprehensive error handling
 */
async function handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
	// Check content type before parsing
	const contentType = response.headers.get('content-type');
	const isJson = contentType?.includes('application/json');

	let data: any;
	try {
		if (isJson) {
			data = await response.json();
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

	if (!response.ok || !data.success) {
		throw new ApiError(
			data.error?.message || 'Request failed',
			data.error?.code || 'UNKNOWN_ERROR',
			data.error?.details
		);
	}

	return data;
}

export const client = {
	async get<T>(path: string, params?: Record<string, string>): Promise<ApiResponse<T>> {
		try {
			const url = new URL(`${API_BASE}${path}`);
			if (params) {
				Object.entries(params).forEach(([key, value]) => {
					url.searchParams.set(key, value);
				});
			}

			const response = await fetchWithTimeout(url.toString());
			return handleResponse<T>(response);
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

	async post<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
		try {
			const response = await fetchWithTimeout(`${API_BASE}${path}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: body ? JSON.stringify(body) : null
			});
			return handleResponse<T>(response);
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

	async postForm<T>(path: string, formData: FormData): Promise<ApiResponse<T>> {
		try {
			const response = await fetchWithTimeout(`${API_BASE}${path}`, {
				method: 'POST',
				body: formData
			});
			return handleResponse<T>(response);
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

	async patch<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
		try {
			const response = await fetchWithTimeout(`${API_BASE}${path}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			return handleResponse<T>(response);
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

	async delete<T>(path: string): Promise<ApiResponse<T>> {
		try {
			const response = await fetchWithTimeout(`${API_BASE}${path}`, {
				method: 'DELETE'
			});
			return handleResponse<T>(response);
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
