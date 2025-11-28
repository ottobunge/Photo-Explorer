<script module lang="ts">
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import Card from './Card.svelte';

	const { Story } = defineMeta({
		title: 'Shared/Card',
		component: Card,
		tags: ['autodocs'],
		argTypes: {
			bordered: {
				control: 'boolean',
				description: 'Whether the card should have a border'
			},
			padded: {
				control: 'boolean',
				description: 'Whether the card should have padding'
			},
			hoverable: {
				control: 'boolean',
				description: 'Whether the card should have hover effects'
			},
			class: {
				control: 'text',
				description: 'Additional CSS classes to apply'
			}
		}
	});
</script>

<!--
@component
Card component provides consistent styling for card-based layouts.

## Usage
```svelte
<Card>
  <h3>Card Title</h3>
  <p>Card content goes here.</p>
</Card>
```
-->

<!-- Default card with border and padding -->
<Story name="Default" args={{ bordered: true, padded: true, hoverable: false }}>
	<h3 style="margin: 0 0 0.5rem; font-size: 1.125rem; font-weight: 600;">Card Title</h3>
	<p style="margin: 0; color: #6b7280;">This is a default card with border and padding.</p>
</Story>

<!-- Card without border -->
<Story name="NoBorder" args={{ bordered: false, padded: true, hoverable: false }}>
	<h3 style="margin: 0 0 0.5rem; font-size: 1.125rem; font-weight: 600;">Card Without Border</h3>
	<p style="margin: 0; color: #6b7280;">This card has no border.</p>
</Story>

<!-- Card without padding -->
<Story name="NoPadding" args={{ bordered: true, padded: false, hoverable: false }}>
	<div style="padding: 1rem;">
		<h3 style="margin: 0 0 0.5rem; font-size: 1.125rem; font-weight: 600;">Card Without Padding</h3>
		<p style="margin: 0; color: #6b7280;">
			This card has no built-in padding. Content manages its own spacing.
		</p>
	</div>
</Story>

<!-- Hoverable card with interactive effects -->
<Story name="Hoverable" args={{ bordered: true, padded: true, hoverable: true }}>
	<h3 style="margin: 0 0 0.5rem; font-size: 1.125rem; font-weight: 600;">Hoverable Card</h3>
	<p style="margin: 0; color: #6b7280;">Hover over this card to see the effect!</p>
</Story>

<!-- Card with image header -->
<Story name="WithImage" args={{ bordered: true, padded: false, hoverable: true }}>
	<div>
		<div
			style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 150px; border-radius: 12px 12px 0 0;"
		></div>
		<div style="padding: 1.5rem;">
			<h3 style="margin: 0 0 0.5rem; font-size: 1.125rem; font-weight: 600;">Photo Album</h3>
			<p style="margin: 0; color: #6b7280;">Summer vacation photos from 2024</p>
			<div style="margin-top: 1rem; font-size: 0.875rem; color: #9ca3af;">52 photos</div>
		</div>
	</div>
</Story>

<!-- Card with actions -->
<Story name="WithActions" args={{ bordered: true, padded: true, hoverable: false }}>
	<div>
		<h3 style="margin: 0 0 0.5rem; font-size: 1.125rem; font-weight: 600;">Google Photos</h3>
		<p style="margin: 0 0 1rem; color: #6b7280;">
			Connect your Google Photos account to sync your photos.
		</p>
		<div style="display: flex; gap: 0.5rem;">
			<button
				style="padding: 0.5rem 1rem; background: #4f46e5; color: white; border: none; border-radius: 6px; cursor: pointer;"
				>Connect</button
			>
			<button
				style="padding: 0.5rem 1rem; background: white; color: #4b5563; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer;"
				>Learn More</button
			>
		</div>
	</div>
</Story>

<!-- Grid of cards -->
<Story name="CardGrid" asChild>
	<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem;">
		<Card hoverable={true}>
			<h3 style="margin: 0 0 0.5rem; font-size: 1rem; font-weight: 600;">Card 1</h3>
			<p style="margin: 0; color: #6b7280; font-size: 0.875rem;">First card in grid</p>
		</Card>
		<Card hoverable={true}>
			<h3 style="margin: 0 0 0.5rem; font-size: 1rem; font-weight: 600;">Card 2</h3>
			<p style="margin: 0; color: #6b7280; font-size: 0.875rem;">Second card in grid</p>
		</Card>
		<Card hoverable={true}>
			<h3 style="margin: 0 0 0.5rem; font-size: 1rem; font-weight: 600;">Card 3</h3>
			<p style="margin: 0; color: #6b7280; font-size: 0.875rem;">Third card in grid</p>
		</Card>
	</div>
</Story>
