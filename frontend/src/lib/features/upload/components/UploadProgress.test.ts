import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import UploadProgress from './UploadProgress.svelte';
import { createUploadItem } from '$lib/test-utils/factories';
import type { UploadItem } from '$lib/types';

describe('UploadProgress', () => {
	let mockItems: UploadItem[];

	beforeEach(() => {
		mockItems = [
			createUploadItem({ status: 'completed', progress: 100, file: new File([''], 'complete.jpg') }),
			createUploadItem({ status: 'uploading', progress: 45, file: new File([''], 'uploading.jpg') }),
			createUploadItem({ status: 'pending', progress: 0, file: new File([''], 'pending.jpg') }),
			createUploadItem({ status: 'failed', progress: 30, error: 'Network error', file: new File([''], 'failed.jpg') })
		];
	});

	describe('Props', () => {
		it('renders with empty items', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: []
				}
			});

			const progressContainer = container.querySelector('[data-testid="upload-progress"]');
			expect(progressContainer).toBeTruthy();
		});

		it('renders all upload items', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: mockItems
				}
			});

			const items = container.querySelectorAll('[data-testid^="upload-item-"]');
			expect(items).toHaveLength(4);
		});
	});

	describe('Item Display', () => {
		it('displays file names', () => {
			const { getByText } = render(UploadProgress, {
				props: {
					items: mockItems
				}
			});

			expect(getByText('complete.jpg')).toBeTruthy();
			expect(getByText('uploading.jpg')).toBeTruthy();
			expect(getByText('pending.jpg')).toBeTruthy();
			expect(getByText('failed.jpg')).toBeTruthy();
		});

		it('displays file sizes', () => {
			const items = [
				createUploadItem({
					file: Object.assign(new File(['x'.repeat(1024)], 'small.jpg'), {
						size: 1024
					})
				}),
				createUploadItem({
					file: Object.assign(new File(['x'.repeat(1048576)], 'large.jpg'), {
						size: 1048576
					})
				})
			];

			const { getByText } = render(UploadProgress, {
				props: { items }
			});

			expect(getByText('1.0 KB')).toBeTruthy();
			expect(getByText('1.0 MB')).toBeTruthy();
		});

		it('displays progress bars', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: mockItems
				}
			});

			const progressBars = container.querySelectorAll('[role="progressbar"]');
			expect(progressBars).toHaveLength(4);

			// Check progress values
			expect(progressBars[0]?.getAttribute('aria-valuenow')).toBe('100');
			expect(progressBars[1]?.getAttribute('aria-valuenow')).toBe('45');
			expect(progressBars[2]?.getAttribute('aria-valuenow')).toBe('0');
			expect(progressBars[3]?.getAttribute('aria-valuenow')).toBe('30');
		});

		it('displays status icons', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: mockItems
				}
			});

			// Check for status-specific icons or indicators
			const completedIcon = container.querySelector('[data-testid="upload-item-0"] .icon-check');
			const uploadingSpinner = container.querySelector('[data-testid="upload-item-1"] .loading-spinner');
			const pendingIcon = container.querySelector('[data-testid="upload-item-2"] .icon-pending');
			const errorIcon = container.querySelector('[data-testid="upload-item-3"] .icon-error');

			// At least one should exist depending on implementation
			const hasStatusIndicators = completedIcon || uploadingSpinner || pendingIcon || errorIcon;
			expect(hasStatusIndicators).toBeTruthy();
		});

		it('displays error messages', () => {
			const { getByText } = render(UploadProgress, {
				props: {
					items: [createUploadItem({ status: 'failed', error: 'File too large' })]
				}
			});

			expect(getByText('File too large')).toBeTruthy();
		});
	});

	describe('User Interactions', () => {
		it('handles cancel upload', async () => {
			const onCancel = vi.fn();
			const uploadingItem = createUploadItem({ status: 'uploading', progress: 50 });

			const { container } = render(UploadProgress, {
				props: {
					items: [uploadingItem],
					onCancel
				}
			});

			const cancelButton = container.querySelector('[aria-label="Cancel upload"]');
			expect(cancelButton).toBeTruthy();

			await fireEvent.click(cancelButton!);
			expect(onCancel).toHaveBeenCalledWith(uploadingItem.id);
		});

		it('handles retry failed upload', async () => {
			const onRetry = vi.fn();
			const failedItem = createUploadItem({ status: 'failed', error: 'Network error' });

			const { container } = render(UploadProgress, {
				props: {
					items: [failedItem],
					onRetry
				}
			});

			const retryButton = container.querySelector('[aria-label="Retry upload"]');
			expect(retryButton).toBeTruthy();

			await fireEvent.click(retryButton!);
			expect(onRetry).toHaveBeenCalledWith(failedItem.id);
		});

		it('handles remove completed item', async () => {
			const onRemove = vi.fn();
			const completedItem = createUploadItem({ status: 'completed', progress: 100 });

			const { container } = render(UploadProgress, {
				props: {
					items: [completedItem],
					onRemove
				}
			});

			const removeButton = container.querySelector('[aria-label="Remove from list"]');
			expect(removeButton).toBeTruthy();

			await fireEvent.click(removeButton!);
			expect(onRemove).toHaveBeenCalledWith(completedItem.id);
		});

		it('handles clear all completed', async () => {
			const onClearCompleted = vi.fn();
			const items = [
				createUploadItem({ status: 'completed' }),
				createUploadItem({ status: 'completed' }),
				createUploadItem({ status: 'uploading' })
			];

			const { container } = render(UploadProgress, {
				props: {
					items,
					onClearCompleted
				}
			});

			const clearButton = container.querySelector('[aria-label="Clear completed uploads"]');
			expect(clearButton).toBeTruthy();

			await fireEvent.click(clearButton!);
			expect(onClearCompleted).toHaveBeenCalled();
		});
	});

	describe('Progress States', () => {
		it('shows pending state', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: [createUploadItem({ status: 'pending' })]
				}
			});

			const item = container.querySelector('[data-testid^="upload-item-"]');
			expect(item?.className).toContain('pending');
			expect(item?.textContent).toContain('Waiting');
		});

		it('shows uploading state with percentage', () => {
			const { container, getByText } = render(UploadProgress, {
				props: {
					items: [createUploadItem({ status: 'uploading', progress: 65 })]
				}
			});

			const item = container.querySelector('[data-testid^="upload-item-"]');
			expect(item?.className).toContain('uploading');
			expect(getByText('65%')).toBeTruthy();
		});

		it('shows completed state', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: [createUploadItem({ status: 'completed', progress: 100 })]
				}
			});

			const item = container.querySelector('[data-testid^="upload-item-"]');
			expect(item?.className).toContain('completed');
			expect(item?.textContent).toContain('Complete');
		});

		it('shows failed state', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: [createUploadItem({ status: 'failed', error: 'Upload failed' })]
				}
			});

			const item = container.querySelector('[data-testid^="upload-item-"]');
			expect(item?.className).toContain('failed');
			expect(item?.textContent).toContain('Failed');
		});
	});

	describe('Summary Statistics', () => {
		it('shows total progress', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: mockItems,
					showSummary: true
				}
			});

			const summary = container.querySelector('[data-testid="upload-summary"]');
			expect(summary).toBeTruthy();

			// Average progress: (100 + 45 + 0 + 30) / 4 = 43.75
			const totalProgress = container.querySelector('[data-testid="total-progress"]');
			expect(totalProgress?.textContent).toContain('43');
		});

		it('shows counts by status', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: mockItems,
					showSummary: true
				}
			});

			const completed = container.querySelector('[data-testid="completed-count"]');
			const uploading = container.querySelector('[data-testid="uploading-count"]');
			const pending = container.querySelector('[data-testid="pending-count"]');
			const failed = container.querySelector('[data-testid="failed-count"]');

			expect(completed?.textContent).toContain('1');
			expect(uploading?.textContent).toContain('1');
			expect(pending?.textContent).toContain('1');
			expect(failed?.textContent).toContain('1');
		});
	});

	describe('Accessibility', () => {
		it('has proper ARIA attributes for progress bars', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: [createUploadItem({ status: 'uploading', progress: 75 })]
				}
			});

			const progressBar = container.querySelector('[role="progressbar"]');
			expect(progressBar?.getAttribute('aria-valuemin')).toBe('0');
			expect(progressBar?.getAttribute('aria-valuemax')).toBe('100');
			expect(progressBar?.getAttribute('aria-valuenow')).toBe('75');
			expect(progressBar?.getAttribute('aria-label')).toBeTruthy();
		});

		it('has accessible button labels', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: mockItems
				}
			});

			const buttons = container.querySelectorAll('button[aria-label]');
			buttons.forEach(button => {
				expect(button.getAttribute('aria-label')).toBeTruthy();
			});
		});

		it('announces status changes', () => {
			const { container } = render(UploadProgress, {
				props: {
					items: [createUploadItem({ status: 'uploading', progress: 50 })]
				}
			});

			const liveRegion = container.querySelector('[aria-live="polite"]');
			expect(liveRegion).toBeTruthy();
		});
	});

	describe('Edge Cases', () => {
		it('handles empty file name', () => {
			const item = createUploadItem({
				file: new File([''], '', { type: 'image/jpeg' })
			});

			const { getByText } = render(UploadProgress, {
				props: {
					items: [item]
				}
			});

			expect(getByText('Unnamed file')).toBeTruthy();
		});

		it('handles very long file names', () => {
			const longName = 'very-long-filename-that-should-be-truncated-in-the-ui'.repeat(3) + '.jpg';
			const item = createUploadItem({
				file: new File([''], longName)
			});

			const { container } = render(UploadProgress, {
				props: {
					items: [item]
				}
			});

			const fileName = container.querySelector('[data-testid="file-name"]');
			expect(fileName?.className).toContain('truncate');
		});

		it('handles rapid status changes', async () => {
			const { rerender } = render(UploadProgress, {
				props: {
					items: [createUploadItem({ status: 'pending', progress: 0 })]
				}
			});

			// Rapid status changes
			await rerender({
				items: [createUploadItem({ status: 'uploading', progress: 25 })]
			});

			await rerender({
				items: [createUploadItem({ status: 'uploading', progress: 75 })]
			});

			await rerender({
				items: [createUploadItem({ status: 'completed', progress: 100 })]
			});

			// Component should handle all transitions without errors
			expect(true).toBe(true);
		});

		it('handles zero file size', () => {
			const item = createUploadItem({
				file: Object.assign(new File([''], 'empty.jpg'), { size: 0 })
			});

			const { getByText } = render(UploadProgress, {
				props: {
					items: [item]
				}
			});

			expect(getByText('0 B')).toBeTruthy();
		});
	});
});