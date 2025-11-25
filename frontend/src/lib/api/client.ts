// API client for Photo Explorer backend

/** Base API host URL - export for use in components that need direct URLs (images, etc.) */
export const API_HOST = import.meta.env['PUBLIC_API_URL'] || 'http://localhost:8000';
const API_BASE = `${API_HOST}/api/v1`;

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

async function handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
	const data = await response.json();

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
		const url = new URL(`${API_BASE}${path}`);
		if (params) {
			Object.entries(params).forEach(([key, value]) => {
				url.searchParams.set(key, value);
			});
		}

		const response = await fetch(url.toString());
		return handleResponse<T>(response);
	},

	async post<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
		const response = await fetch(`${API_BASE}${path}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: body ? JSON.stringify(body) : null
		});
		return handleResponse<T>(response);
	},

	async postForm<T>(path: string, formData: FormData): Promise<ApiResponse<T>> {
		const response = await fetch(`${API_BASE}${path}`, {
			method: 'POST',
			body: formData
		});
		return handleResponse<T>(response);
	},

	async patch<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
		const response = await fetch(`${API_BASE}${path}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		return handleResponse<T>(response);
	},

	async delete<T>(path: string): Promise<ApiResponse<T>> {
		const response = await fetch(`${API_BASE}${path}`, {
			method: 'DELETE'
		});
		return handleResponse<T>(response);
	}
};

export { ApiError };
