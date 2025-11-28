# Refactoring Example: Search Route

This document shows a concrete example of refactoring the search route to use the new URL state utilities.

## Current Implementation (search/+page.svelte)

The current implementation has approximately 80 lines of URL-related code:

```typescript
// URL parsing (lines 64-101)
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

const perPage = $derived.by(() => {
  const urlPerPage = $page.url.searchParams.get('per_page');
  if (urlPerPage !== null) {
    const parsed = parseInt(urlPerPage, 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= 100) {
      return parsed;
    }
  }
  return 24;
});

const selectedConnectorId = $derived($page.url.searchParams.get('connector_id'));
const selectedAlbumId = $derived($page.url.searchParams.get('album_id'));

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

// URL building (lines 145-182)
function updateUrl(params: {
  query?: string;
  page?: number;
  perPage?: number;
  connectorId?: string | null;
  albumId?: string | null;
  similarityThreshold?: number;
}): void {
  const urlParams = new URLSearchParams();

  const finalQuery = params.query !== undefined ? params.query : query;
  const finalPage = params.page !== undefined ? params.page : currentPage;
  const finalPerPage = params.perPage !== undefined ? params.perPage : perPage;
  const finalConnectorId = params.connectorId !== undefined ? params.connectorId : selectedConnectorId;
  const finalAlbumId = params.albumId !== undefined ? params.albumId : selectedAlbumId;
  const finalThreshold = params.similarityThreshold !== undefined ? params.similarityThreshold : similarityThreshold;

  if (finalQuery.trim()) {
    urlParams.set('q', finalQuery);
  }
  if (finalPage > 1) {
    urlParams.set('page', finalPage.toString());
  }
  if (finalPerPage !== 24) {
    urlParams.set('per_page', finalPerPage.toString());
  }
  if (finalConnectorId) {
    urlParams.set('connector_id', finalConnectorId);
  }
  if (finalAlbumId) {
    urlParams.set('album_id', finalAlbumId);
  }
  urlParams.set('similarity_threshold', finalThreshold.toString());

  const newUrl = urlParams.toString() ? `?${urlParams.toString()}` : '/search';
  void goto(newUrl, { replaceState: true, keepFocus: true });
}
```

## Refactored Implementation

Using the URL state utilities reduces this to ~20 lines:

```typescript
import {
  useUrlParam,
  useUrlParamNumber,
  useUrlParamNullable,
  updateUrlParams
} from '$lib/utils/urlState.svelte';

// URL parsing - concise and type-safe
const query = $derived(useUrlParam($page, 'q', ''));
const currentPage = $derived(useUrlParamNumber($page, 'page', 1, { min: 1 }));
const perPage = $derived(useUrlParamNumber($page, 'per_page', 24, { min: 1, max: 100 }));
const selectedConnectorId = $derived(useUrlParamNullable($page, 'connector_id'));
const selectedAlbumId = $derived(useUrlParamNullable($page, 'album_id'));
const similarityThreshold = $derived(
  useUrlParamNumber($page, 'similarity_threshold', 0.18, {
    min: 0.0,
    max: 1.0,
    allowDecimals: true
  })
);

// URL building - simplified
function updateUrl(params: {
  query?: string;
  page?: number;
  perPage?: number;
  connectorId?: string | null;
  albumId?: string | null;
  similarityThreshold?: number;
}): void {
  updateUrlParams(params, $page.url.searchParams);
}
```

## Benefits of Refactoring

### 1. Code Reduction
- **Before**: ~80 lines of URL-related code
- **After**: ~20 lines
- **Reduction**: 75% less code

### 2. Type Safety
All validation logic is type-checked:
```typescript
// Compile-time error if min/max are wrong types
const page = $derived(useUrlParamNumber($page, 'page', 1, { min: 1 }));

// Type inference ensures correct return type
const threshold: number = $derived(
  useUrlParamNumber($page, 'similarity_threshold', 0.18, {
    min: 0.0,
    max: 1.0,
    allowDecimals: true
  })
);
```

### 3. Eliminated Duplication
The same validation logic is reused across all routes:
- No more copy-pasting number parsing
- No more manual range validation
- No more boolean parsing variations

### 4. Better Testability
The utilities are tested once (50+ unit tests), not in each component:
```typescript
// This is tested in urlState.test.ts
expect(useUrlParamNumber(page, 'page', 1, { min: 1 })).toBe(1);
expect(useUrlParamNumber(page, 'page', 1, { min: 1, max: 999 })).toBe(1);
```

### 5. Consistency
All routes now use the same pattern:
```typescript
// Search page
const query = $derived(useUrlParam($page, 'q', ''));

// Faces page
const view = $derived(useUrlParamEnum<TabType>($page, 'view', 'list', ['list', 'graph']));

// Photos page
const sortBy = $derived(useUrlParamEnum<SortBy>($page, 'sort', 'date', ['date', 'name']));
```

## Migration Steps

1. **Add import** at the top of the file:
   ```typescript
   import {
     useUrlParam,
     useUrlParamNumber,
     useUrlParamNullable,
     updateUrlParams
   } from '$lib/utils/urlState.svelte';
   ```

2. **Replace URL parsing** (lines 64-101):
   - Find all `$derived($page.url.searchParams.get(...))`
   - Replace with appropriate `useUrlParam*` function
   - Keep wrapped in `$derived(...)`

3. **Simplify `updateUrl` function** (lines 145-182):
   - Replace entire function body with single `updateUrlParams` call
   - Remove manual URLSearchParams building
   - Remove parameter merging logic

4. **Test the refactoring**:
   - Run the app and verify URL behavior
   - Test browser back/forward buttons
   - Test direct URL navigation
   - Verify all edge cases (invalid values, missing params)

5. **Remove unused code**:
   - No need to import/use `URLSearchParams`
   - Parser functions are handled by utilities

## Side-by-Side Comparison

### Parsing a Number with Range Validation

**Before:**
```typescript
const perPage = $derived.by(() => {
  const urlPerPage = $page.url.searchParams.get('per_page');
  if (urlPerPage !== null) {
    const parsed = parseInt(urlPerPage, 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= 100) {
      return parsed;
    }
  }
  return 24;
});
```

**After:**
```typescript
const perPage = $derived(
  useUrlParamNumber($page, 'per_page', 24, { min: 1, max: 100 })
);
```

### Parsing a Float with Range Validation

**Before:**
```typescript
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
```

**After:**
```typescript
const similarityThreshold = $derived(
  useUrlParamNumber($page, 'similarity_threshold', 0.18, {
    min: 0.0,
    max: 1.0,
    allowDecimals: true
  })
);
```

### Updating Multiple URL Parameters

**Before:**
```typescript
function updateUrl(params: { ... }): void {
  const urlParams = new URLSearchParams();
  const finalQuery = params.query !== undefined ? params.query : query;
  const finalPage = params.page !== undefined ? params.page : currentPage;
  // ... 30 more lines ...
  const newUrl = urlParams.toString() ? `?${urlParams.toString()}` : '/search';
  void goto(newUrl, { replaceState: true, keepFocus: true });
}
```

**After:**
```typescript
function updateUrl(params: { ... }): void {
  updateUrlParams(params, $page.url.searchParams);
}
```

## Performance Impact

No negative performance impact:
- Utilities are simple pure functions
- No additional DOM access or rendering
- Same number of reactive dependencies
- Slightly better due to less code execution

## Backward Compatibility

The refactoring maintains 100% backward compatibility:
- Same URL format
- Same parameter names
- Same validation rules
- Same default values

Existing bookmarks and shared URLs continue to work.

## Next Steps

After refactoring the search route, apply the same pattern to:
1. `/routes/faces/+page.svelte` - Tab and filter state
2. `/routes/photos/+page.svelte` - Pagination and filters
3. Any other routes with URL-driven state

## Questions?

See:
- `urlState.svelte.ts` - Full API documentation
- `urlState.test.ts` - Comprehensive test examples
- `URL_STATE_MIGRATION.md` - Complete migration guide
