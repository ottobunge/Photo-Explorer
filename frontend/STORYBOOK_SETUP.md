# Storybook Setup - Photo Explorer Frontend

Storybook 10.1.0 has been successfully installed and configured for the Photo Explorer frontend.

## Installation Summary

- **Storybook Version**: 10.1.0
- **Framework**: @storybook/sveltekit (SvelteKit integration)
- **Builder**: Vite

## Installed Packages

```json
{
  "@storybook/sveltekit": "^10.1.0",
  "@storybook/addon-svelte-csf": "^5.0.10",
  "@storybook/addon-a11y": "^10.1.0",
  "@chromatic-com/storybook": "^4.1.3",
  "storybook": "^10.1.0"
}
```

## Configuration Files

### Main Configuration (`.storybook/main.ts`)

```typescript
import type { StorybookConfig } from '@storybook/sveltekit';

const config: StorybookConfig = {
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(js|ts|svelte)'],
  addons: [
    '@storybook/addon-svelte-csf',
    '@chromatic-com/storybook',
    '@storybook/addon-a11y'
  ],
  framework: {
    name: '@storybook/sveltekit',
    options: {}
  },
  docs: {
    autodocs: 'tag'
  }
};
export default config;
```

### Preview Configuration (`.storybook/preview.ts`)

- Tailwind CSS imported via `../src/app.css`
- Configured viewport presets (mobile, tablet, desktop)
- Background color options (light, dark, gray)
- Accessibility testing enabled with 'todo' mode

## Running Storybook

```bash
# Development mode (with hot reload)
npm run storybook

# Build static version for deployment
npm run build-storybook
```

Storybook runs on http://localhost:6006

## Created Stories

Six shared components now have comprehensive story files:

### 1. Button (`Button.stories.ts`)

- All variants (primary, secondary, ghost)
- All sizes (sm, md, lg)
- Disabled state
- Comparison stories showing all variants/sizes

### 2. LoadingSpinner (`LoadingSpinner.stories.ts`)

- All size variants
- Centered layout example
- Comparison showing all sizes

### 3. StatusBadge (`StatusBadge.stories.ts`)

- All status types (connected, disconnected, syncing, error, success, warning, info)
- Custom label examples
- Dot visibility options
- Comparison showing all statuses

### 4. Card (`Card.stories.ts`)

- Border and padding variations
- Hoverable effect
- With image header
- With action buttons
- Grid layout example

### 5. EmptyState (`EmptyState.stories.ts`)

- Various use cases (no photos, no search results, no connectors, etc.)
- With action buttons
- Multiple action buttons
- Minimal variants

### 6. Modal (`Modal.stories.ts`)

- Basic modal with/without title
- Confirmation dialog pattern
- Form modal
- Long scrolling content
- Success/error messages
- With images

## Documentation

### Welcome Page (`src/stories/Welcome.mdx`)

Comprehensive introduction to Storybook including:
- What is Storybook
- Getting started guide
- Component organization
- Writing stories
- Testing with Storybook
- Best practices
- Resources

### Configuration README (`.storybook/README.md`)

Technical documentation covering:
- File structure
- Running Storybook
- Addon configuration
- Tailwind CSS integration
- Creating stories (with templates)
- Control types
- Rendering slots and snippets
- Accessibility testing
- Best practices
- Troubleshooting

## Enabled Addons

### @storybook/addon-svelte-csf

Enables writing stories in Svelte Component Story Format (CSF)

### @chromatic-com/storybook

Visual regression testing integration for Chromatic

### @storybook/addon-a11y

**Accessibility Testing**

Automatically tests stories for WCAG compliance:
- Color contrast
- ARIA attributes
- Keyboard navigation
- Focus management

Current configuration: `test: 'todo'` (shows violations but doesn't fail)

To fail CI on violations, change to `test: 'error'` in `.storybook/preview.ts`

## Features

### Tailwind CSS Integration

Full Tailwind CSS support with all utility classes available in stories. The main `app.css` file is imported in preview configuration.

### Viewport Testing

Three responsive breakpoints configured:
- **Mobile**: 375px × 667px
- **Tablet**: 768px × 1024px
- **Desktop**: 1280px × 800px

Use the viewport toolbar to test components at different screen sizes.

### Background Testing

Three background options:
- **Light**: #ffffff (default)
- **Dark**: #1f2937
- **Gray**: #f9fafb

### Autodocs

All components with `tags: ['autodocs']` get automatic documentation pages generated from:
- Component props (argTypes)
- JSDoc comments
- Story descriptions

## Story File Locations

All story files are co-located with their components:

```
src/lib/shared/components/
├── Button.svelte
├── Button.stories.ts
├── Card.svelte
├── Card.stories.ts
├── EmptyState.svelte
├── EmptyState.stories.ts
├── LoadingSpinner.svelte
├── LoadingSpinner.stories.ts
├── Modal.svelte
├── Modal.stories.ts
├── StatusBadge.svelte
└── StatusBadge.stories.ts
```

## Next Steps

### Add Feature Component Stories

Create stories for feature-specific components:

1. **Search Components**
   - SearchBar
   - SearchResults
   - SimilarityThresholdSlider

2. **Photo Components**
   - PhotoGrid
   - PhotoCard
   - PhotoDetail

3. **Face Components**
   - FaceCluster
   - FaceGrid
   - ClusterMergeModal

4. **Album Components**
   - AlbumCard
   - AlbumGrid
   - AlbumDetail

5. **Settings Components**
   - ConnectorCard
   - SettingsSection
   - ModelsSection

### Interaction Testing

Add `@storybook/addon-interactions` for testing user interactions:

```bash
npm install --save-dev @storybook/addon-interactions @storybook/test
```

### Visual Regression Testing

Set up Chromatic for automated visual regression testing:

```bash
npx chromatic --project-token=<your-token>
```

### Component Testing with Vitest

Stories can serve as test cases. Consider adding:

```bash
npm install --save-dev @storybook/test-runner
```

## Troubleshooting

### Tailwind classes not applying

Ensure `../src/app.css` is imported in `.storybook/preview.ts`

### Component not rendering

- Check that all required props are provided in story args
- Ensure component doesn't depend on SvelteKit-specific runtime features
- Use relative or aliased imports (`$lib/...`)

### SvelteKit-specific features

If a component uses SvelteKit features (`$app/navigation`, `$app/stores`, etc.), you may need to mock them in `.storybook/preview.ts`

### Svelte 5 runes

Storybook 10.1.0 fully supports Svelte 5 with runes. For components using snippets:

```typescript
export const WithSnippet: Story = {
  render: () => ({
    Component: MyComponent,
    template: `
      <MyComponent>
        {#snippet action()}
          <Button>Action</Button>
        {/snippet}
      </MyComponent>
    `
  })
};
```

## Resources

- [Storybook Documentation](https://storybook.js.org/docs)
- [SvelteKit Storybook Integration](https://github.com/storybookjs/storybook/tree/next/code/frameworks/sveltekit)
- [Svelte 5 Documentation](https://svelte.dev/docs/svelte/overview)
- [Accessibility Testing](https://storybook.js.org/addons/@storybook/addon-a11y)
- [Photo Explorer Architecture](../CLAUDE.md)

## Summary

Storybook is now fully configured and operational with:

- 6 shared components documented with comprehensive stories
- Tailwind CSS integration
- Accessibility testing
- Responsive viewport testing
- Automatic documentation generation
- Welcome page and technical documentation

Start Storybook with `npm run storybook` and visit http://localhost:6006 to explore the component library.
