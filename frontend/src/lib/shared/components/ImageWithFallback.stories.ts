import type { Meta, StoryObj } from '@storybook/sveltekit';
import ImageWithFallback from './ImageWithFallback.svelte';

/**
 * ImageWithFallback component provides automatic error handling and fallback display.
 *
 * ## Usage
 * ```svelte
 * <ImageWithFallback
 *   src="/photos/image.jpg"
 *   alt="Description"
 *   fallback="🖼️"
 * />
 * ```
 */
// @ts-ignore - Svelte 5 component type incompatibility with Storybook
const meta = {
	title: 'Shared/ImageWithFallback',
	component: ImageWithFallback,
	tags: ['autodocs'],
	argTypes: {
		src: {
			control: 'text',
			description: 'Image source URL'
		},
		alt: {
			control: 'text',
			description: 'Alt text for accessibility'
		},
		fallback: {
			control: 'text',
			description: 'Fallback image URL or emoji'
		},
		class: {
			control: 'text',
			description: 'Additional CSS classes'
		},
		lazy: {
			control: 'boolean',
			description: 'Whether to use lazy loading'
		}
	}
} satisfies Meta<ImageWithFallback>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Successful image load
 */
export const Default: Story = {
	args: {
		src: 'https://picsum.photos/400/300',
		alt: 'Random photo',
		lazy: true
	}
};

/**
 * Broken image with emoji fallback
 */
export const BrokenImageEmoji: Story = {
	args: {
		src: 'https://invalid-url-that-will-fail.example.com/image.jpg',
		alt: 'Failed to load',
		fallback: '🖼️'
	}
};

/**
 * Broken image with custom emoji
 */
export const BrokenImageCustomEmoji: Story = {
	args: {
		src: 'https://invalid-url-that-will-fail.example.com/image.jpg',
		alt: 'Failed to load',
		fallback: '📷'
	}
};

/**
 * Square aspect ratio image
 */
export const SquareImage: Story = {
	args: {
		src: 'https://picsum.photos/400/400',
		alt: 'Square photo',
		class: 'rounded-lg'
	}
};

/**
 * Wide landscape image
 */
export const LandscapeImage: Story = {
	args: {
		src: 'https://picsum.photos/800/400',
		alt: 'Landscape photo',
		class: 'rounded-lg'
	}
};

/**
 * Portrait orientation image
 */
export const PortraitImage: Story = {
	args: {
		src: 'https://picsum.photos/400/600',
		alt: 'Portrait photo',
		class: 'rounded-lg'
	}
};

/**
 * Image with custom styling
 */
export const WithCustomStyling: Story = {
	args: {
		src: 'https://picsum.photos/400/300',
		alt: 'Styled photo',
		class: 'rounded-xl shadow-lg border-4 border-primary-500'
	}
};

/**
 * Eager loading (no lazy load)
 */
export const EagerLoading: Story = {
	args: {
		src: 'https://picsum.photos/400/300?random=1',
		alt: 'Eager loaded photo',
		lazy: false
	}
};

/**
 * Image gallery grid
 */
export const ImageGrid: Story = {
	render: () => ({
		Component: ImageWithFallback,
		template: `
			<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
				<ImageWithFallback
					src="https://picsum.photos/200/200?random=1"
					alt="Photo 1"
					class="rounded-lg"
				/>
				<ImageWithFallback
					src="https://picsum.photos/200/200?random=2"
					alt="Photo 2"
					class="rounded-lg"
				/>
				<ImageWithFallback
					src="https://picsum.photos/200/200?random=3"
					alt="Photo 3"
					class="rounded-lg"
				/>
				<ImageWithFallback
					src="https://invalid-url.example.com/1.jpg"
					alt="Failed photo 1"
					fallback="📷"
					class="rounded-lg"
				/>
				<ImageWithFallback
					src="https://picsum.photos/200/200?random=4"
					alt="Photo 4"
					class="rounded-lg"
				/>
				<ImageWithFallback
					src="https://invalid-url.example.com/2.jpg"
					alt="Failed photo 2"
					fallback="🖼️"
					class="rounded-lg"
				/>
			</div>
		`
	})
};

/**
 * Different fallback styles
 */
export const FallbackVariations: Story = {
	render: () => ({
		Component: ImageWithFallback,
		template: `
			<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
				<div style="text-align: center;">
					<ImageWithFallback
						src="https://invalid-url.example.com/1.jpg"
						alt="Camera fallback"
						fallback="📷"
						class="rounded-lg"
						style="height: 150px;"
					/>
					<div style="margin-top: 0.5rem; font-size: 0.75rem; color: #6b7280;">Camera</div>
				</div>
				<div style="text-align: center;">
					<ImageWithFallback
						src="https://invalid-url.example.com/2.jpg"
						alt="Picture fallback"
						fallback="🖼️"
						class="rounded-lg"
						style="height: 150px;"
					/>
					<div style="margin-top: 0.5rem; font-size: 0.75rem; color: #6b7280;">Picture</div>
				</div>
				<div style="text-align: center;">
					<ImageWithFallback
						src="https://invalid-url.example.com/3.jpg"
						alt="Photo fallback"
						fallback="📸"
						class="rounded-lg"
						style="height: 150px;"
					/>
					<div style="margin-top: 0.5rem; font-size: 0.75rem; color: #6b7280;">Photo</div>
				</div>
				<div style="text-align: center;">
					<ImageWithFallback
						src="https://invalid-url.example.com/4.jpg"
						alt="Image fallback"
						fallback="🌄"
						class="rounded-lg"
						style="height: 150px;"
					/>
					<div style="margin-top: 0.5rem; font-size: 0.75rem; color: #6b7280;">Landscape</div>
				</div>
			</div>
		`
	})
};

/**
 * Loading states
 */
export const LoadingState: Story = {
	args: {
		src: 'https://picsum.photos/400/300?grayscale',
		alt: 'Loading photo',
		class: 'rounded-lg'
	},
	parameters: {
		docs: {
			description: {
				story: 'Images show a loading state with blur effect until fully loaded'
			}
		}
	}
};

/**
 * Photo card pattern
 */
export const PhotoCard: Story = {
	render: () => ({
		Component: ImageWithFallback,
		template: `
			<div style="max-width: 300px; background: white; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">
				<ImageWithFallback
					src="https://picsum.photos/300/200"
					alt="Photo card"
					class="w-full"
					style="height: 200px; object-fit: cover;"
				/>
				<div style="padding: 1rem;">
					<h3 style="margin: 0 0 0.5rem; font-size: 1rem; font-weight: 600;">Photo Title</h3>
					<p style="margin: 0; color: #6b7280; font-size: 0.875rem;">Beach sunset on a summer evening</p>
					<div style="margin-top: 1rem; display: flex; gap: 0.5rem; font-size: 0.75rem; color: #9ca3af;">
						<span>📅 2024-01-15</span>
						<span>📍 California</span>
					</div>
				</div>
			</div>
		`
	})
};
