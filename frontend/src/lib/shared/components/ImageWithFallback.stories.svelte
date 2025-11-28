<script module lang="ts">
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import ImageWithFallback from './ImageWithFallback.svelte';

	const { Story } = defineMeta({
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
				description: 'Fallback content when image fails to load'
			},
			class: {
				control: 'text',
				description: 'Additional CSS classes'
			},
			lazy: {
				control: 'boolean',
				description: 'Enable lazy loading'
			}
		}
	});
</script>

<!--
@component
ImageWithFallback component provides an image with fallback handling.

## Usage
```svelte
<ImageWithFallback
  src="/photo.jpg"
  alt="Beach sunset"
  fallback="📷"
  lazy={true}
/>
```
-->

<!-- Successful image load -->
<Story
	name="Success"
	args={{
		src: '/src/stories/assets/avif-test-image.avif',
		alt: 'Test image',
		lazy: false
	}}
/>

<!-- Image with error (triggers fallback) -->
<Story
	name="WithFallback"
	args={{
		src: '/nonexistent-image.jpg',
		alt: 'Missing image',
		fallback: '📷',
		lazy: false
	}}
/>

<!-- Lazy loaded image -->
<Story
	name="LazyLoaded"
	args={{
		src: '/src/stories/assets/avif-test-image.avif',
		alt: 'Lazy loaded image',
		lazy: true
	}}
/>

<!-- Custom fallback with emoji -->
<Story
	name="CustomFallback"
	args={{
		src: '/broken-image.jpg',
		alt: 'Broken image',
		fallback: '🖼️',
		lazy: false
	}}
/>

<!-- With custom class -->
<Story
	name="WithCustomClass"
	args={{
		src: '/src/stories/assets/avif-test-image.avif',
		alt: 'Styled image',
		class: 'rounded-lg shadow-lg',
		lazy: false
	}}
/>
