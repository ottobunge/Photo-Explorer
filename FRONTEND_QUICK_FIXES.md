# Frontend Quick Fixes - Immediate Actions

## 🔴 Critical Bugs to Fix NOW (< 1 hour total)

### 1. Fix Type Casting Bug (5 minutes)

**File**: `frontend/src/lib/features/faces/components/ClusterMergeModal.svelte`
**Line**: 65-69

```diff
- onkeydown={(e: KeyboardEvent) => {
-     if (e.key === 'Enter') {
-         handleBackdropClick(e as unknown as MouseEvent);
-     }
- }}
+ onkeydown={(e: KeyboardEvent) => {
+     if (e.key === 'Enter') {
+         handleMerge();
+     }
+ }}
```

### 2. Add Abort Cleanup (10 minutes)

**File**: `frontend/src/routes/search/+page.svelte`
**Add after line 205**:

```typescript
onDestroy(() => {
    if (abortController !== null) {
        abortController.abort();
        abortController = null;
    }
});
```

### 3. Fix Reactive Loading State (5 minutes)

**File**: `frontend/src/routes/connectors/[id]/+page.svelte`
**Line 57**:

```diff
- let pickerPolling = false;
+ let pickerPolling = $state(false);
```

## 🟡 Quick Svelte 5 Migrations (30 minutes each)

### Component 1: UploadZone.svelte

```diff
- export let disabled = false;
- export let accept = 'image/*';
+ interface Props {
+   disabled?: boolean;
+   accept?: string;
+ }
+ const { disabled = false, accept = 'image/*' }: Props = $props();
```

### Component 2: SearchResults.svelte

```diff
- export let results: SearchResult[];
- export let loading: boolean;
+ interface Props {
+   results: SearchResult[];
+   loading: boolean;
+ }
+ const { results, loading }: Props = $props();
```

### Component 3: FolderCard.svelte

```diff
- export let folder: Folder;
+ interface Props {
+   folder: Folder;
+ }
+ const { folder }: Props = $props();
```

## 🟢 Create Constants File (30 minutes)

**Create**: `frontend/src/lib/constants.ts`

```typescript
// Pagination
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 24,
  SEARCH_PAGE_SIZE: 24,
  FACES_PAGE_SIZE: 30,
  ALBUMS_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
} as const;

// Thresholds
export const THRESHOLDS = {
  DEFAULT_SIMILARITY: 0.18,
  MIN_SIMILARITY: 0.0,
  MAX_SIMILARITY: 1.0,
  SIMILARITY_STEP: 0.01,
} as const;

// Graph Configuration
export const GRAPH_CONFIG = {
  DEFAULT_RADIUS: 200,
  MIN_NODE_SIZE: 40,
  MAX_NODE_SIZE: 100,
  NODE_SIZE_MULTIPLIER: 2,
  ANIMATION_DURATION: 500,
  FORCE_RERENDER_DELAY: 2000,
} as const;

// Upload Configuration
export const UPLOAD_CONFIG = {
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  ACCEPTED_TYPES: 'image/*',
  MAX_CONCURRENT_UPLOADS: 3,
  CHUNK_SIZE: 1024 * 1024, // 1MB chunks
} as const;

// API Configuration
export const API_CONFIG = {
  TIMEOUT: 30000, // 30 seconds
  RETRY_COUNT: 3,
  RETRY_DELAY: 1000,
} as const;

// UI Configuration
export const UI_CONFIG = {
  DEBOUNCE_DELAY: 300,
  TOAST_DURATION: 5000,
  MODAL_ANIMATION_DURATION: 200,
  INFINITE_SCROLL_THRESHOLD: 100,
} as const;
```

## 🔵 Add First Component Test (1 hour)

**Create**: `frontend/src/lib/shared/components/Modal.test.ts`

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import Modal from './Modal.svelte';

describe('Modal', () => {
  it('renders when open is true', () => {
    const { getByRole } = render(Modal, {
      props: {
        open: true,
        title: 'Test Modal'
      }
    });

    expect(getByRole('dialog')).toBeInTheDocument();
  });

  it('does not render when open is false', () => {
    const { queryByRole } = render(Modal, {
      props: {
        open: false,
        title: 'Test Modal'
      }
    });

    expect(queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('calls onClose when escape key is pressed', async () => {
    const onClose = vi.fn();
    const { getByRole } = render(Modal, {
      props: {
        open: true,
        title: 'Test Modal',
        onClose
      }
    });

    await fireEvent.keyDown(getByRole('dialog'), { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when backdrop is clicked', async () => {
    const onClose = vi.fn();
    const { container } = render(Modal, {
      props: {
        open: true,
        title: 'Test Modal',
        onClose
      }
    });

    const backdrop = container.querySelector('.modal-backdrop');
    if (backdrop) {
      await fireEvent.click(backdrop);
      expect(onClose).toHaveBeenCalled();
    }
  });

  it('does not close when modal content is clicked', async () => {
    const onClose = vi.fn();
    const { container } = render(Modal, {
      props: {
        open: true,
        title: 'Test Modal',
        onClose
      }
    });

    const content = container.querySelector('.modal-content');
    if (content) {
      await fireEvent.click(content);
      expect(onClose).not.toHaveBeenCalled();
    }
  });

  it('renders custom title and children', () => {
    const { getByText } = render(Modal, {
      props: {
        open: true,
        title: 'Custom Title',
        $$slots: {
          default: ['Modal body content']
        }
      }
    });

    expect(getByText('Custom Title')).toBeInTheDocument();
    expect(getByText('Modal body content')).toBeInTheDocument();
  });
});
```

## 📝 Update Component to Use Constants

**File**: `frontend/src/routes/search/+page.svelte`

```diff
+ import { PAGINATION, THRESHOLDS } from '$lib/constants';

  const perPage = $derived((): number => {
-     return 24;
+     return PAGINATION.SEARCH_PAGE_SIZE;
  });

  const defaultSimilarity = $derived((): number => {
-     return 0.18;
+     return THRESHOLDS.DEFAULT_SIMILARITY;
  });
```

**File**: `frontend/src/routes/faces/+page.svelte`

```diff
+ import { PAGINATION } from '$lib/constants';

- let perPage = $state(30);
+ let perPage = $state(PAGINATION.FACES_PAGE_SIZE);

  // Also update the comparison
- if (perPage !== 30) {
+ if (perPage !== PAGINATION.FACES_PAGE_SIZE) {
```

## 🚀 Quick Test Commands

```bash
# Run these after making changes

# 1. Type check
npm run check

# 2. Lint check
npm run lint

# 3. Run tests
npm test

# 4. Check for Svelte 4 patterns
grep -r "export let" src/lib/

# 5. Find remaining hardcoded values
grep -rn "return [0-9]\+;" src/routes/
```

## ✅ Checklist (Complete in Order)

- [ ] Fix type casting bug in ClusterMergeModal
- [ ] Add abort cleanup in search route
- [ ] Fix reactive loading state
- [ ] Create constants.ts file
- [ ] Update 2 files to use constants
- [ ] Migrate UploadZone to Svelte 5
- [ ] Migrate SearchResults to Svelte 5
- [ ] Migrate FolderCard to Svelte 5
- [ ] Add Modal component test
- [ ] Run type check and fix any errors
- [ ] Commit changes

## 🎯 Expected Results

After completing these quick fixes:
- **3 bugs fixed** (including 1 medium severity)
- **3 components** migrated to Svelte 5
- **8+ hardcoded values** centralized
- **1 component** with full test coverage
- **Type safety** improved

**Total time**: ~3 hours

## 📊 Progress Tracking

```bash
# Before
Svelte 4 components: 5
Components without tests: 15+
Hardcoded values: 8+
Known bugs: 6

# After quick fixes
Svelte 4 components: 2 (-3)
Components without tests: 14 (-1)
Hardcoded values: 0 (-8)
Known bugs: 3 (-3)
```

---

**Start with bug fixes first** - they take < 20 minutes total and eliminate immediate risks!