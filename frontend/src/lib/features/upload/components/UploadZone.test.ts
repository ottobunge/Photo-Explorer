import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import UploadZone from './UploadZone.svelte';
import { createDragEvent } from '$lib/test-utils/mocks';

describe('UploadZone', () => {
	let mockFileSelectedHandler: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		mockFileSelectedHandler = vi.fn();
	});

	describe('Props', () => {
		it('renders with default props', () => {
			const { container } = render(UploadZone, {
				props: {}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]');
			expect(zone).toBeTruthy();
			expect(zone?.className).toContain('border-dashed');
		});

		it('applies disabled state', () => {
			const { container } = render(UploadZone, {
				props: {
					disabled: true
				}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]');
			expect(zone?.className).toContain('opacity-50');
			expect(zone?.className).toContain('cursor-not-allowed');

			const input = container.querySelector('input[type="file"]');
			expect(input?.hasAttribute('disabled')).toBe(true);
		});

		it('sets custom accept attribute', () => {
			const { container } = render(UploadZone, {
				props: {
					accept: '.jpg,.png'
				}
			});

			const input = container.querySelector('input[type="file"]');
			expect(input?.getAttribute('accept')).toBe('.jpg,.png');
		});

		it('defaults to accepting all images', () => {
			const { container } = render(UploadZone, {
				props: {}
			});

			const input = container.querySelector('input[type="file"]');
			expect(input?.getAttribute('accept')).toBe('image/*');
		});
	});

	describe('Drag and Drop', () => {
		it('shows drag over state when dragging files', async () => {
			const { container } = render(UploadZone, {
				props: {}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;

			// Create drag event with files
			const dragEvent = createDragEvent('dragover', [
				new File(['test'], 'test.jpg', { type: 'image/jpeg' })
			]);

			await fireEvent(zone, dragEvent);

			expect(zone.className).toContain('border-primary-500');
			expect(zone.className).toContain('bg-primary-50');
		});

		it('removes drag over state on drag leave', async () => {
			const { container } = render(UploadZone, {
				props: {}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;

			// Enter drag state
			await fireEvent.dragOver(zone);

			// Leave drag state
			await fireEvent.dragLeave(zone);

			expect(zone.className).toContain('border-gray-300');
			expect(zone.className).toContain('bg-gray-50');
		});

		it('handles file drop', async () => {
			const onFilesSelected = vi.fn();
			const { container } = render(UploadZone, {
				props: {
					onFilesSelected
				}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;
			const files = [
				new File(['image1'], 'photo1.jpg', { type: 'image/jpeg' }),
				new File(['image2'], 'photo2.png', { type: 'image/png' })
			];

			const dropEvent = createDragEvent('drop', files);
			await fireEvent(zone, dropEvent);

			expect(onFilesSelected).toHaveBeenCalledWith(files);
		});

		it('filters non-image files during drop', async () => {
			const onFilesSelected = vi.fn();
			const { container } = render(UploadZone, {
				props: {
					onFilesSelected
				}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;
			const files = [
				new File(['image'], 'photo.jpg', { type: 'image/jpeg' }),
				new File(['text'], 'document.pdf', { type: 'application/pdf' }),
				new File(['text'], 'readme.txt', { type: 'text/plain' })
			];

			const dropEvent = createDragEvent('drop', files);
			await fireEvent(zone, dropEvent);

			expect(onFilesSelected).toHaveBeenCalledWith([files[0]]); // Only image file
		});

		it('does not process drop when disabled', async () => {
			const onFilesSelected = vi.fn();
			const { container } = render(UploadZone, {
				props: {
					disabled: true,
					onFilesSelected
				}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;
			const files = [new File(['test'], 'test.jpg', { type: 'image/jpeg' })];

			const dropEvent = createDragEvent('drop', files);
			await fireEvent(zone, dropEvent);

			expect(onFilesSelected).not.toHaveBeenCalled();
		});

		it('does not show drag over state when disabled', async () => {
			const { container } = render(UploadZone, {
				props: {
					disabled: true
				}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;

			await fireEvent.dragOver(zone);

			// Should remain in disabled state
			expect(zone.className).toContain('opacity-50');
			expect(zone.className).not.toContain('border-primary-500');
		});
	});

	describe('File Selection', () => {
		it('opens file dialog on click', async () => {
			const { container } = render(UploadZone, {
				props: {}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;
			const input = container.querySelector('input[type="file"]')!;

			// Mock click on input
			const clickSpy = vi.spyOn(input, 'click');

			await fireEvent.click(zone);

			expect(clickSpy).toHaveBeenCalled();
		});

		it('handles file selection from dialog', async () => {
			const onFilesSelected = vi.fn();
			const { container } = render(UploadZone, {
				props: {
					onFilesSelected
				}
			});

			const input = container.querySelector('input[type="file"]')!;
			const files = [
				new File(['test1'], 'photo1.jpg', { type: 'image/jpeg' }),
				new File(['test2'], 'photo2.jpg', { type: 'image/jpeg' })
			];

			// Mock file selection
			Object.defineProperty(input, 'files', {
				value: files,
				writable: false
			});

			await fireEvent.change(input);

			expect(onFilesSelected).toHaveBeenCalledWith(files);
		});

		it('clears input value after selection', async () => {
			const onFilesSelected = vi.fn();
			const { container } = render(UploadZone, {
				props: {
					onFilesSelected
				}
			});

			const input = container.querySelector('input[type="file"]')!;
			const file = new File(['test'], 'photo.jpg', { type: 'image/jpeg' });

			Object.defineProperty(input, 'files', {
				value: [file],
				writable: false
			});

			await fireEvent.change(input);

			// Input value should be cleared
			expect(input.value).toBe('');
		});

		it('does not open file dialog when disabled', async () => {
			const { container } = render(UploadZone, {
				props: {
					disabled: true
				}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;
			const input = container.querySelector('input[type="file"]')!;
			const clickSpy = vi.spyOn(input, 'click');

			await fireEvent.click(zone);

			expect(clickSpy).not.toHaveBeenCalled();
		});
	});

	describe('Keyboard Interactions', () => {
		it('opens file dialog on Enter key', async () => {
			const { container } = render(UploadZone, {
				props: {}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;
			const input = container.querySelector('input[type="file"]')!;
			const clickSpy = vi.spyOn(input, 'click');

			await fireEvent.keyDown(zone, { key: 'Enter' });

			expect(clickSpy).toHaveBeenCalled();
		});

		it('opens file dialog on Space key', async () => {
			const { container } = render(UploadZone, {
				props: {}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;
			const input = container.querySelector('input[type="file"]')!;
			const clickSpy = vi.spyOn(input, 'click');

			await fireEvent.keyDown(zone, { key: ' ' });

			expect(clickSpy).toHaveBeenCalled();
		});

		it('does not respond to keyboard when disabled', async () => {
			const { container } = render(UploadZone, {
				props: {
					disabled: true
				}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;
			const input = container.querySelector('input[type="file"]')!;
			const clickSpy = vi.spyOn(input, 'click');

			await fireEvent.keyDown(zone, { key: 'Enter' });
			await fireEvent.keyDown(zone, { key: ' ' });

			expect(clickSpy).not.toHaveBeenCalled();
		});
	});

	describe('Rendering', () => {
		it('displays upload icon', () => {
			const { container } = render(UploadZone, {
				props: {}
			});

			const icon = container.querySelector('.text-5xl');
			expect(icon?.textContent).toBe('📷');
		});

		it('displays drag and drop text', () => {
			const { getByText } = render(UploadZone, {
				props: {}
			});

			expect(getByText('Drag & drop photos here')).toBeTruthy();
			expect(getByText('or click to select files')).toBeTruthy();
		});

		it('displays supported formats', () => {
			const { getByText } = render(UploadZone, {
				props: {}
			});

			expect(getByText('Supports JPEG, PNG, WebP, HEIC')).toBeTruthy();
		});

		it('updates text during drag over', async () => {
			const { container, getByText } = render(UploadZone, {
				props: {}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;

			await fireEvent.dragOver(zone);

			expect(getByText('Drop photos here')).toBeTruthy();
		});
	});

	describe('Accessibility', () => {
		it('has proper role and tabindex', () => {
			const { container } = render(UploadZone, {
				props: {}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]');
			expect(zone?.getAttribute('role')).toBe('button');
			expect(zone?.getAttribute('tabindex')).toBe('0');
		});

		it('has negative tabindex when disabled', () => {
			const { container } = render(UploadZone, {
				props: {
					disabled: true
				}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]');
			expect(zone?.getAttribute('tabindex')).toBe('-1');
		});

		it('hidden input is not focusable', () => {
			const { container } = render(UploadZone, {
				props: {}
			});

			const input = container.querySelector('input[type="file"]');
			expect(input?.className).toContain('hidden');
		});
	});

	describe('Edge Cases', () => {
		it('handles empty file list', async () => {
			const onFilesSelected = vi.fn();
			const { container } = render(UploadZone, {
				props: {
					onFilesSelected
				}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;
			const dropEvent = createDragEvent('drop', []);

			await fireEvent(zone, dropEvent);

			expect(onFilesSelected).not.toHaveBeenCalled();
		});

		it('handles null dataTransfer', async () => {
			const onFilesSelected = vi.fn();
			const { container } = render(UploadZone, {
				props: {
					onFilesSelected
				}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;
			const dropEvent = new Event('drop', { bubbles: true }) as DragEvent;

			await fireEvent(zone, dropEvent);

			expect(onFilesSelected).not.toHaveBeenCalled();
		});

		it('prevents default drag behaviors', async () => {
			const { container } = render(UploadZone, {
				props: {}
			});

			const zone = container.querySelector('[data-testid="upload-zone"]')!;
			const dragEvent = createDragEvent('dragover', []);
			const dropEvent = createDragEvent('drop', []);

			const preventDefaultSpy = vi.spyOn(dragEvent, 'preventDefault');
			const preventDefaultDropSpy = vi.spyOn(dropEvent, 'preventDefault');

			await fireEvent(zone, dragEvent);
			await fireEvent(zone, dropEvent);

			expect(preventDefaultSpy).toHaveBeenCalled();
			expect(preventDefaultDropSpy).toHaveBeenCalled();
		});
	});
});