# Storybook Configuration

This directory contains the Storybook configuration for the Photo Explorer frontend.

## Files

- `main.ts` - Core Storybook configuration (stories location, addons, framework)
- `preview.ts` - Global decorators, parameters, and styles
- `vitest.setup.ts` - Vitest integration for component testing

## Running Storybook

```bash
# Development mode (hot reload)
npm run storybook

# Build static version
npm run build-storybook

# Test stories with Vitest
npm run test:storybook
```

## Configuration

### Stories Location

Stories are auto-discovered from:
- `src/**/*.stories.@(js|ts|svelte)`
- `src/**/*.mdx` (documentation pages)

### Enabled Addons

1. **@storybook/addon-svelte-csf** - Svelte Component Story Format support
2. **@storybook/addon-essentials** - Core addons bundle
   - Controls - Interactive props
   - Actions - Event logging
   - Docs - Auto documentation
   - Viewport - Responsive testing
   - Backgrounds - Background color testing
3. **@storybook/addon-a11y** - Accessibility testing
4. **@storybook/addon-vitest** - Vitest integration for component testing
5. **@chromatic-com/storybook** - Visual regression testing

### Tailwind CSS Integration

Tailwind CSS is automatically loaded via the import in `preview.ts`:

```typescript
import '../src/app.css';
```

This ensures all Tailwind utilities are available in stories.

## Creating Stories

### File Location

Place story files next to the component they document:

```
src/lib/shared/components/
├── Button.svelte
└── Button.stories.ts
```

### Story Template

```typescript
import type { Meta, StoryObj } from '@storybook/svelte';
import YourComponent from './YourComponent.svelte';

const meta = {
  title: 'Category/YourComponent',
  component: YourComponent,
  tags: ['autodocs'],
  argTypes: {
    prop: {
      control: 'text',
      description: 'Prop description'
    }
  }
} satisfies Meta<YourComponent>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    prop: 'default value'
  }
};
```

### Control Types

Common control types for argTypes:

- `text` - String input
- `number` - Number input
- `boolean` - Checkbox
- `select` - Dropdown (requires `options: ['a', 'b', 'c']`)
- `radio` - Radio buttons (requires `options`)
- `color` - Color picker
- `date` - Date picker
- `object` - JSON editor
- `array` - Array editor

### Rendering Slots

For components with slots:

```typescript
export const WithSlot: Story = {
  render: (args) => ({
    Component: YourComponent,
    props: args,
    slots: {
      default: '<p>Slot content</p>'
    }
  })
};
```

### Rendering Snippets (Svelte 5)

For components using Svelte 5 snippets:

```typescript
export const WithSnippet: Story = {
  render: () => ({
    Component: YourComponent,
    template: `
      <YourComponent>
        {#snippet action()}
          <Button>Action</Button>
        {/snippet}
      </YourComponent>
    `
  })
};
```

## Accessibility Testing

The a11y addon is configured to show violations in the test UI:

```typescript
a11y: {
  test: 'todo' // Shows violations but doesn't fail
}
```

To fail CI on accessibility violations:

```typescript
a11y: {
  test: 'error'
}
```

## Viewport Configuration

Three default viewports are configured:

- **Mobile**: 375px × 667px
- **Tablet**: 768px × 1024px
- **Desktop**: 1280px × 800px

Use the viewport toolbar to test responsive designs.

## Background Configuration

Three default backgrounds:

- **light**: #ffffff (default)
- **dark**: #1f2937
- **gray**: #f9fafb

## Component Testing with Vitest

Stories can be tested with Vitest using the addon:

```bash
npm run test:storybook
```

This runs all stories as Vitest tests, ensuring they render without errors.

## Best Practices

### Story Organization

1. **Default story** - Show the most common usage
2. **Variant stories** - One story per variant
3. **State stories** - Show different states (loading, error, success)
4. **Edge cases** - Long text, empty states, etc.
5. **Combination story** - All variants together for visual comparison

### Documentation

1. Add JSDoc comments to the meta object for component-level documentation
2. Add descriptions to all argTypes
3. Create MDX files for complex documentation
4. Use code examples in JSDoc comments

### Naming Conventions

- Story file: `ComponentName.stories.ts`
- Meta title: `Category/ComponentName`
- Story names: `PascalCase` (e.g., `Default`, `WithIcon`, `LargeSize`)

### Testing

1. Test all prop variations
2. Test all slot variations
3. Test accessibility (a11y addon)
4. Test responsive behavior (viewport addon)
5. Add interaction tests for interactive components

## Troubleshooting

### Tailwind classes not working

Ensure `../src/app.css` is imported in `preview.ts`.

### Component not rendering

Check that:
1. The component is exported properly
2. All required props are provided in args
3. The component doesn't depend on SvelteKit-specific features (`$app/*`)

### Svelte 5 runes issues

Storybook supports Svelte 5. If you encounter issues:
1. Ensure you're using the latest `@storybook/svelte-vite`
2. Use the `render` function for components with snippets
3. Check the template syntax in complex render functions

### Import errors

For shared components, use absolute imports:

```typescript
import Button from '$lib/shared/components/Button.svelte';
```

Or relative imports:

```typescript
import Button from './Button.svelte';
```

## Additional Resources

- [Storybook for Svelte](https://storybook.js.org/docs/svelte/get-started/introduction)
- [Storybook Addons](https://storybook.js.org/addons)
- [Svelte 5 Documentation](https://svelte.dev/docs/svelte/overview)
- [Tailwind CSS](https://tailwindcss.com/docs)
