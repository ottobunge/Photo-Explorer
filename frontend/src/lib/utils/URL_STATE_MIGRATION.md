# URL State Management - Migration Guide

This guide shows how to refactor existing URL-driven state code to use the reusable `urlState` utilities.

## Overview

The `urlState` utilities provide a type-safe, DRY approach to URL-driven state management following the "URL as single source of truth" pattern.

## Benefits

- **Type Safety**: Full TypeScript support with generic constraints
- **Validation**: Built-in validation for numbers (min/max), enums, and booleans
- **Reusability**: No more copy-pasting URL parsing logic
- **Consistency**: Standardized patterns across the application
- **Testing**: Utilities are fully tested with 50+ unit tests

## Before: Manual URL Parsing

```typescript
// Old approach (repetitive and error-prone)
const query = $derived($page.url.searchParams.get('q') ?? '');

const currentPage = $derived.by(() => {
  const urlPage = $page.url.searchParams.get('page');
  if (urlPage !== null) {
    const parsed = parseInt(urlPage, 10);
    if (!isNaN(parsed) && parsed >= 1) {
      return parsed;
    }
  }
  return 1;
});

const similarityThreshold = $derived.by(() => {
  const urlSimilarity = $page.url.searchParams.get('similarity_threshold');
  if (urlSimilarity !== null) {
    const parsed = parseFloat(urlSimilarity);
    if (!isNaN(parsed) && parsed >= 0.0 && parsed <= 1.0) {
      return parsed;
    }
  }
  return 0.18;
});

const selectedConnectorId = $derived($page.url.searchParams.get('connector_id'));
```

## After: Using URL State Utilities

```typescript
import {
  useUrlParam,
  useUrlParamNumber,
  useUrlParamNullable
} from '$lib/utils/urlState.svelte';

// Clean and concise
const query = $derived(useUrlParam($page, 'q', ''));

const currentPage = $derived(
  useUrlParamNumber($page, 'page', 1, { min: 1 })
);

const similarityThreshold = $derived(
  useUrlParamNumber($page, 'similarity_threshold', 0.18, {
    min: 0.0,
    max: 1.0,
    allowDecimals: true
  })
);

const selectedConnectorId = $derived(
  useUrlParamNullable($page, 'connector_id')
);
```

## Complete Example: Search Page

### Before

```typescript
<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';

  // Manual URL parsing
  const query = $derived($page.url.searchParams.get('q') ?? '');
  const currentPage = $derived.by(() => {
    const urlPage = $page.url.searchParams.get('page');
    const parsed = urlPage ? parseInt(urlPage, 10) : null;
    return (parsed && parsed >= 1) ? parsed : 1;
  });
  const perPage = $derived.by(() => {
    const urlPerPage = $page.url.searchParams.get('per_page');
    const parsed = urlPerPage ? parseInt(urlPerPage, 10) : null;
    return (parsed && parsed >= 1 && parsed <= 100) ? parsed : 24;
  });

  // Manual URL building
  function updateUrl(params: { query?: string; page?: number; perPage?: number }) {
    const urlParams = new URLSearchParams();
    const finalQuery = params.query !== undefined ? params.query : query;
    const finalPage = params.page !== undefined ? params.page : currentPage;
    const finalPerPage = params.perPage !== undefined ? params.perPage : perPage;

    if (finalQuery.trim()) urlParams.set('q', finalQuery);
    if (finalPage > 1) urlParams.set('page', finalPage.toString());
    if (finalPerPage !== 24) urlParams.set('per_page', finalPerPage.toString());

    const newUrl = urlParams.toString() ? `?${urlParams.toString()}` : '/search';
    void goto(newUrl, { replaceState: true, keepFocus: true });
  }
</script>
```

### After

```typescript
<script lang="ts">
  import { page } from '$app/stores';
  import {
    useUrlParam,
    useUrlParamNumber,
    updateUrlParams
  } from '$lib/utils/urlState.svelte';

  // Clean URL parsing
  const query = $derived(useUrlParam($page, 'q', ''));
  const currentPage = $derived(useUrlParamNumber($page, 'page', 1, { min: 1 }));
  const perPage = $derived(useUrlParamNumber($page, 'per_page', 24, { min: 1, max: 100 }));

  // Simple URL updating
  function updateUrl(params: { query?: string; page?: number; perPage?: number }) {
    updateUrlParams(params, $page.url.searchParams);
  }
</script>
```

## API Reference

### Reading URL Parameters

#### `useUrlParam<T>(page, key, defaultValue, parser?, validator?)`
Generic parameter parser with optional custom logic.

```typescript
const sortBy = $derived(useUrlParam($page, 'sort', 'name'));
```

#### `useUrlParamNumber(page, key, defaultValue, options?)`
Parse numbers with validation.

```typescript
const page = $derived(useUrlParamNumber($page, 'page', 1, {
  min: 1,
  max: 999
}));

const threshold = $derived(useUrlParamNumber($page, 'threshold', 0.5, {
  min: 0.0,
  max: 1.0,
  allowDecimals: true
}));
```

#### `useUrlParamBoolean(page, key, defaultValue)`
Parse boolean values (accepts: true/false, 1/0, yes/no).

```typescript
const enabled = $derived(useUrlParamBoolean($page, 'enabled', false));
```

#### `useUrlParamEnum<T>(page, key, defaultValue, allowedValues)`
Type-safe enum parsing.

```typescript
type SortBy = 'name' | 'date' | 'size';
const sortBy = $derived(useUrlParamEnum<SortBy>(
  $page,
  'sort',
  'name',
  ['name', 'date', 'size']
));
```

#### `useUrlParamNullable(page, key)`
Get optional string parameters (returns null if missing).

```typescript
const connectorId = $derived(useUrlParamNullable($page, 'connector_id'));
```

### Updating URL Parameters

#### `updateUrlParams(updates, currentParams, options?)`
Update multiple parameters at once.

```typescript
updateUrlParams(
  { query: 'beach', page: 1, sort: 'date' },
  $page.url.searchParams
);

// Remove parameter by setting to null
updateUrlParams({ filter: null }, $page.url.searchParams);
```

#### `updateUrlParam(key, value, currentParams, options?)`
Update a single parameter (convenience wrapper).

```typescript
updateUrlParam('page', 2, $page.url.searchParams);
updateUrlParam('filter', null, $page.url.searchParams); // Remove
```

## Migration Checklist

When refactoring a route to use URL state utilities:

1. **Import utilities** at the top of your component
2. **Replace manual parsing** with appropriate `useUrlParam*` functions
3. **Wrap in $derived** for reactivity
4. **Replace manual URL building** with `updateUrlParams` or `updateUrlParam`
5. **Remove custom validation logic** (handled by utilities)
6. **Add tests** for component behavior

## Common Patterns

### Pagination

```typescript
const currentPage = $derived(useUrlParamNumber($page, 'page', 1, { min: 1 }));
const perPage = $derived(useUrlParamNumber($page, 'per_page', 24, { min: 1, max: 100 }));

function goToPage(newPage: number) {
  updateUrlParam('page', newPage, $page.url.searchParams);
}
```

### Filters

```typescript
const connectorId = $derived(useUrlParamNullable($page, 'connector_id'));
const albumId = $derived(useUrlParamNullable($page, 'album_id'));

function clearFilters() {
  updateUrlParams(
    { connector_id: null, album_id: null },
    $page.url.searchParams
  );
}
```

### Tabs

```typescript
type TabType = 'list' | 'graph';
const activeTab = $derived(
  useUrlParamEnum<TabType>($page, 'view', 'list', ['list', 'graph'])
);

function setTab(tab: TabType) {
  updateUrlParam('view', tab, $page.url.searchParams);
}
```

### Search with Threshold

```typescript
const query = $derived(useUrlParam($page, 'q', ''));
const threshold = $derived(
  useUrlParamNumber($page, 'similarity_threshold', 0.18, {
    min: 0.0,
    max: 1.0,
    allowDecimals: true
  })
);

function updateSearch(newQuery: string, newThreshold: number) {
  updateUrlParams(
    { q: newQuery, similarity_threshold: newThreshold, page: 1 },
    $page.url.searchParams
  );
}
```

## Testing

The utilities are fully tested and handle edge cases:
- Invalid numbers (NaN, out of range)
- Invalid booleans
- Invalid enum values
- Missing parameters
- Null/undefined values

See `urlState.test.ts` for comprehensive test examples.

## Type Safety

All utilities are fully typed with TypeScript:
- Generic types for custom parsing
- Enum types for allowed values
- Strict null checks
- Exact optional property types

The TypeScript compiler will catch misuse at compile time.
