# Search Route Refactor: URL as Single Source of Truth

**Date**: 2025-11-27
**File**: `/home/otto/repos/personal/photo-explorer/frontend/src/routes/search/+page.svelte`

## Problem

The search route had a **dual-source-of-truth anti-pattern**:

1. Used `onMount()` to read URL params and initialize local state
2. Maintained separate `$state` variables for bookmarkable data (query, page, filters)
3. Updated URL **after** API calls completed via `updateUrl()`
4. No reactivity to URL changes (browser back/forward wouldn't work)

### Example of the Anti-Pattern

```typescript
// BAD: Dual source of truth
let query = $state('');
let currentPage = $state(1);

onMount(() => {
  const urlQuery = $page.url.searchParams.get('q');
  if (urlQuery !== null) {
    query = urlQuery;  // Copy URL -> local state
  }
  // ... more copying
});

async function handleSearch() {
  // Uses local state
  const res = await fetch(`/search?q=${query}&page=${currentPage}`);
  updateUrl();  // Update URL AFTER fetch
}
```

## Solution

Refactored to use **URL as single source of truth**:

1. All bookmarkable state derived from `$page.url.searchParams` using `$derived`
2. URL updates happen **before** data fetching (via `goto()`)
3. Data fetching triggered reactively via `$effect` when URL changes
4. Browser back/forward now works correctly

### Key Changes

#### 1. Derive Bookmarkable State from URL

```typescript
// GOOD: URL is the source of truth
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
  return 0.18; // Default
});
```

#### 2. Reactive Data Fetching

```typescript
// React to URL changes and fetch data
$effect(() => {
  // Track dependencies to trigger re-fetch when URL params change
  void query;
  void currentPage;
  void selectedConnectorId;
  void selectedAlbumId;
  void similarityThreshold;

  if (isSearchMode && query.trim()) {
    void fetchSearchResults();
  } else {
    void fetchPhotos();
  }
});
```

#### 3. Update URL Before Fetching

```typescript
function updateUrl(params: {
  query?: string;
  page?: number;
  perPage?: number;
  connectorId?: string | null;
  albumId?: string | null;
  similarityThreshold?: number;
}): void {
  const urlParams = new URLSearchParams();
  // ... build params
  const newUrl = urlParams.toString() ? `?${urlParams.toString()}` : '/search';
  void goto(newUrl, { replaceState: true, keepFocus: true });
}

function goToPage(newPage: number): void {
  if (newPage >= 1 && newPage <= totalPages) {
    updateUrl({ page: newPage });  // URL update triggers $effect -> fetch
  }
}
```

#### 4. Handle Search Input

Since `query` is now read-only (derived from URL), we maintain a separate local state for the search input that syncs to URL on submit:

```typescript
// Local search input state (syncs to URL on submit)
let searchInput = $state('');

// Sync search input with URL query when it changes (e.g., browser back/forward)
$effect(() => {
  searchInput = query;
});

function onSearchSubmit(newQuery: string): void {
  updateUrl({ query: newQuery, page: 1 });
}
```

## Benefits

1. **Bookmarkable**: Users can share URLs with filters applied
2. **Browser navigation works**: Back/forward buttons work correctly
3. **Single source of truth**: No synchronization bugs between URL and state
4. **Cleaner code**: No manual `onMount()` initialization
5. **Reactive**: Changes to URL automatically trigger data fetching

## State Classification

### URL State (Bookmarkable)
- `query` - Search query
- `currentPage` - Current page number
- `perPage` - Items per page
- `selectedConnectorId` - Filter by connector
- `selectedAlbumId` - Filter by album
- `similarityThreshold` - Similarity threshold for search results

### UI-Only State (Ephemeral)
- `photos` - Photo data (fetched from API)
- `loading` - Loading indicator
- `total` - Total count
- `connectors` - Available connectors for filter dropdown
- `albums` - Available albums for filter dropdown
- `searchInput` - Temporary search input before submit
- `abortController` - Request cancellation

## Testing

The refactor maintains all existing functionality:
- Search works correctly
- Pagination works
- Filters (connector, album, similarity threshold) work
- Browser back/forward navigation now works (new feature!)
- URL parameters are preserved (bookmarkable)

## Migration Pattern for Other Routes

Other routes with similar issues should follow this pattern:

1. Identify bookmarkable state (filters, page numbers, sort order, etc.)
2. Convert from `$state` to `$derived` based on `$page.url.searchParams`
3. Create `updateUrl()` function that uses `goto()`
4. Use `$effect()` to trigger side effects (API calls) when URL changes
5. Keep UI-only state (loading, errors, expanded panels) as `$state`

## Files Modified

- `/home/otto/repos/personal/photo-explorer/frontend/src/routes/search/+page.svelte`

## Related Documentation

- [Svelte 5 Runes](https://svelte.dev/docs/svelte/$derived)
- [SvelteKit page store](https://kit.svelte.dev/docs/modules#$app-stores-page)
- [Photo Explorer CLAUDE.md](../CLAUDE.md) - URL-as-single-source-of-truth pattern
