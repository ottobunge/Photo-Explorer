import { describe, it, expect, beforeEach, vi } from 'vitest';
import { client, ApiError, API_HOST } from './client';

// Mock fetch globally
global.fetch = vi.fn();

describe('API Client', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe('Network Error Handling', () => {
		it('should handle network failures', async () => {
			(global.fetch as any).mockRejectedValue(new Error('Network failure'));

			await expect(client.get('/test')).rejects.toThrow(ApiError);
			await expect(client.get('/test')).rejects.toThrow('Network error');
		});

		it('should handle CORS errors', async () => {
			(global.fetch as any).mockRejectedValue(new TypeError('Failed to fetch'));

			await expect(client.get('/test')).rejects.toThrow(ApiError);
			await expect(client.get('/test')).rejects.toThrow('Network error');
		});

		it('should handle timeout errors', async () => {
			// Mock AbortController to trigger timeout
			const mockAbort = vi.fn();
			global.AbortController = vi.fn().mockImplementation(() => ({
				abort: mockAbort,
				signal: { aborted: false }
			})) as any;

			(global.fetch as any).mockImplementation(
				() => Promise.reject(Object.assign(new Error('The operation was aborted'), { name: 'AbortError' }))
			);

			await expect(client.get('/test')).rejects.toThrow(ApiError);
			await expect(client.get('/test')).rejects.toThrow('timeout');
		});
	});

	describe('Response Parsing', () => {
		it('should handle non-JSON responses', async () => {
			(global.fetch as any).mockResolvedValue({
				ok: false,
				status: 500,
				statusText: 'Internal Server Error',
				headers: new Map([['content-type', 'text/html']]),
				text: async () => '<html>Error page</html>'
			});

			await expect(client.get('/test')).rejects.toThrow(ApiError);
			await expect(client.get('/test')).rejects.toThrow('non-JSON response');
		});

		it('should handle invalid JSON responses', async () => {
			(global.fetch as any).mockResolvedValue({
				ok: true,
				headers: new Map([['content-type', 'application/json']]),
				json: async () => {
					throw new Error('Invalid JSON');
				}
			});

			await expect(client.get('/test')).rejects.toThrow(ApiError);
			await expect(client.get('/test')).rejects.toThrow('Failed to parse');
		});

		it('should parse successful JSON responses', async () => {
			const mockData = { id: '123', name: 'Test' };
			(global.fetch as any).mockResolvedValue({
				ok: true,
				headers: new Map([['content-type', 'application/json']]),
				json: async () => ({ success: true, data: mockData })
			});

			const result = await client.get('/test');
			expect(result.success).toBe(true);
			expect(result.data).toEqual(mockData);
		});
	});

	describe('HTTP Methods', () => {
		it('should make GET requests with query params', async () => {
			(global.fetch as any).mockResolvedValue({
				ok: true,
				headers: new Map([['content-type', 'application/json']]),
				json: async () => ({ success: true, data: {} })
			});

			await client.get('/test', { params: { page: '1', limit: '10' } });

			expect(global.fetch).toHaveBeenCalledWith(
				expect.stringContaining('/test?page=1&limit=10'),
				expect.any(Object)
			);
		});

		it('should make POST requests with JSON body', async () => {
			(global.fetch as any).mockResolvedValue({
				ok: true,
				headers: new Map([['content-type', 'application/json']]),
				json: async () => ({ success: true, data: {} })
			});

			const body = { name: 'Test' };
			await client.post('/test', body);

			expect(global.fetch).toHaveBeenCalledWith(
				expect.any(String),
				expect.objectContaining({
					method: 'POST',
					headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
					body: JSON.stringify(body)
				})
			);
		});

		it('should make PATCH requests', async () => {
			(global.fetch as any).mockResolvedValue({
				ok: true,
				headers: new Map([['content-type', 'application/json']]),
				json: async () => ({ success: true, data: {} })
			});

			await client.patch('/test', { name: 'Updated' });

			expect(global.fetch).toHaveBeenCalledWith(
				expect.any(String),
				expect.objectContaining({ method: 'PATCH' })
			);
		});

		it('should make DELETE requests', async () => {
			(global.fetch as any).mockResolvedValue({
				ok: true,
				headers: new Map([['content-type', 'application/json']]),
				json: async () => ({ success: true, data: {} })
			});

			await client.delete('/test');

			expect(global.fetch).toHaveBeenCalledWith(
				expect.any(String),
				expect.objectContaining({ method: 'DELETE' })
			);
		});

		it('should make POST requests with FormData', async () => {
			(global.fetch as any).mockResolvedValue({
				ok: true,
				headers: new Map([['content-type', 'application/json']]),
				json: async () => ({ success: true, data: { uploaded: [], failed: [] } })
			});

			const formData = new FormData();
			formData.append('file', new Blob(['test']), 'test.jpg');
			await client.postForm('/upload', formData);

			expect(global.fetch).toHaveBeenCalledWith(
				expect.any(String),
				expect.objectContaining({
					method: 'POST',
					body: formData
				})
			);
		});
	});

	describe('Error Response Handling', () => {
		it('should throw ApiError with error details from server', async () => {
			(global.fetch as any).mockResolvedValue({
				ok: false,
				status: 400,
				headers: new Map([['content-type', 'application/json']]),
				json: async () => ({
					success: false,
					error: {
						code: 'VALIDATION_ERROR',
						message: 'Invalid input',
						details: { field: 'name' }
					}
				})
			});

			try {
				await client.get('/test');
				expect.fail('Should have thrown an error');
			} catch (error) {
				expect(error).toBeInstanceOf(ApiError);
				if (error instanceof ApiError) {
					expect(error.message).toBe('Invalid input');
					expect(error.code).toBe('VALIDATION_ERROR');
					expect(error.details).toEqual({ field: 'name' });
				}
			}
		});

		it('should provide default error message for unknown errors', async () => {
			(global.fetch as any).mockResolvedValue({
				ok: false,
				status: 500,
				headers: new Map([['content-type', 'application/json']]),
				json: async () => ({ success: false })
			});

			try {
				await client.get('/test');
				expect.fail('Should have thrown an error');
			} catch (error) {
				expect(error).toBeInstanceOf(ApiError);
				if (error instanceof ApiError) {
					expect(error.message).toBe('Request failed');
					expect(error.code).toBe('UNKNOWN_ERROR');
				}
			}
		});
	});

	describe('API Base URL', () => {
		it('should use correct API base URL', () => {
			expect(API_HOST).toBeDefined();
			expect(API_HOST).toMatch(/^http/);
		});
	});
});
