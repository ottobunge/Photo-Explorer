# Storybook Quick Start Guide

## Run Storybook

```bash
cd /home/otto/repos/personal/photo-explorer/frontend
npm run storybook
```

Storybook will start at: **http://localhost:6006**

## What's Included

### 7 Component Stories Created

All shared components now have comprehensive Storybook documentation:

1. **Button** - All variants (primary, secondary, ghost) and sizes
2. **Card** - Container component with border, padding, and hover options
3. **EmptyState** - Placeholder states for empty content
4. **ImageWithFallback** - Image component with error handling
5. **LoadingSpinner** - Loading indicators in multiple sizes
6. **Modal** - Dialog overlays for focused interactions
7. **StatusBadge** - Status indicators with colors

### Documentation Pages

- **Welcome** (`src/stories/Welcome.mdx`) - Introduction and getting started
- **Configure** (`src/stories/Configure.mdx`) - Auto-generated configuration guide

## Enabled Features

### Tailwind CSS
Full Tailwind CSS support with all utility classes available

### Responsive Testing
Three viewport presets:
- Mobile (375px)
- Tablet (768px)
- Desktop (1280px)

### Accessibility Testing
Automatic WCAG compliance checks on all stories

### Auto-Documentation
Components with `tags: ['autodocs']` get automatic docs pages

## File Structure

```
frontend/
├── .storybook/
│   ├── main.ts           # Core configuration
│   ├── preview.ts        # Global settings
│   └── README.md         # Technical documentation
├── src/
│   ├── lib/
│   │   └── shared/
│   │       └── components/
│   │           ├── Button.svelte
│   │           ├── Button.stories.ts
│   │           ├── Card.svelte
│   │           ├── Card.stories.ts
│   │           └── ... (other components)
│   └── stories/
│       ├── Welcome.mdx
│       └── Configure.mdx
├── STORYBOOK_SETUP.md    # Detailed setup documentation
└── STORYBOOK_QUICKSTART.md (this file)
```

## Creating New Stories

### Basic Template

Create a `.stories.ts` file next to your component:

```typescript
import type { Meta, StoryObj } from '@storybook/sveltekit';
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
    prop: 'value'
  }
};
```

### With Slots

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

### With Svelte 5 Snippets

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

## Common Tasks

### Build Static Storybook

```bash
npm run build-storybook
```

Output: `storybook-static/` directory

### Test Accessibility

1. Open any story
2. Click "Accessibility" tab in addons panel
3. View WCAG violations and passes

### Test Responsive Design

1. Open any story
2. Click viewport icon in toolbar
3. Select Mobile/Tablet/Desktop preset

### Change Background

1. Open any story
2. Click background icon in toolbar
3. Select Light/Dark/Gray

## Next Steps

1. **Add feature component stories** for search, photos, faces, albums
2. **Set up Chromatic** for visual regression testing
3. **Add interaction tests** using @storybook/addon-interactions
4. **Deploy Storybook** to share with team

## Resources

- Detailed setup: [STORYBOOK_SETUP.md](./STORYBOOK_SETUP.md)
- Technical docs: [.storybook/README.md](./.storybook/README.md)
- Storybook docs: https://storybook.js.org/docs
- SvelteKit integration: https://github.com/storybookjs/storybook/tree/next/code/frameworks/sveltekit

## Troubleshooting

**Tailwind not working?**
- Verify `../src/app.css` is imported in `.storybook/preview.ts`

**Component not rendering?**
- Check all required props are provided
- Ensure component doesn't use SvelteKit runtime features

**SvelteKit features needed?**
- Mock `$app/navigation`, `$app/stores` in `.storybook/preview.ts`

For more help, see [.storybook/README.md](./.storybook/README.md)
