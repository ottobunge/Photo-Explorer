import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import UploadZone from './UploadZone.svelte';

describe('UploadZone', () => {
	it('renders upload zone with instructions', () => {
		render(UploadZone);

		expect(screen.getByText('Drag & drop photos here')).toBeInTheDocument();
		expect(screen.getByText('or click to select files')).toBeInTheDocument();
	});

	it('is focusable for keyboard accessibility', () => {
		render(UploadZone);

		const zone = screen.getByTestId('upload-zone');
		expect(zone).toHaveAttribute('tabindex', '0');
	});

	it('shows drag over state when files are dragged over', async () => {
		render(UploadZone);

		const zone = screen.getByTestId('upload-zone');

		await fireEvent.dragOver(zone);

		expect(screen.getByText('Drop photos here')).toBeInTheDocument();
	});

	it('removes drag over state on drag leave', async () => {
		render(UploadZone);

		const zone = screen.getByTestId('upload-zone');

		await fireEvent.dragOver(zone);
		await fireEvent.dragLeave(zone);

		expect(screen.getByText('Drag & drop photos here')).toBeInTheDocument();
	});

	it('is disabled when disabled prop is true', () => {
		render(UploadZone, { props: { disabled: true } });

		const zone = screen.getByTestId('upload-zone');
		expect(zone).toHaveAttribute('tabindex', '-1');
		expect(zone).toHaveClass('opacity-50');
	});

	it('dispatches filesSelected event on file drop', async () => {
		const { component } = render(UploadZone);

		const handler = vi.fn();
		component.$on('filesSelected', handler);

		const zone = screen.getByTestId('upload-zone');

		const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
		const dataTransfer = {
			files: [file]
		};

		await fireEvent.drop(zone, { dataTransfer });

		expect(handler).toHaveBeenCalled();
	});

	it('filters out non-image files on drop', async () => {
		const { component } = render(UploadZone);

		const handler = vi.fn();
		component.$on('filesSelected', handler);

		const zone = screen.getByTestId('upload-zone');

		const pdfFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
		const jpgFile = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
		const dataTransfer = {
			files: [pdfFile, jpgFile]
		};

		await fireEvent.drop(zone, { dataTransfer });

		expect(handler).toHaveBeenCalledWith(
			expect.objectContaining({
				detail: [jpgFile]
			})
		);
	});
});
