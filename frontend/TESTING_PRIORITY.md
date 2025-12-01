# Frontend Testing Priority Plan

## 📊 Test Coverage Audit

### Current State
- **Components with tests**: 3/39 (7.7% coverage)
  - ✅ PhotoGrid
  - ✅ ClusterPicker
  - ✅ SimilarityThresholdSlider

- **Stores with tests**: 8 stores have test coverage

### Components Missing Tests (36 total)

## 🎯 Priority Matrix

### Priority 1: Core Shared Components (HIGH IMPACT)
These are used across the entire application:

| Component | Usage | Complexity | Test Priority |
|-----------|-------|------------|---------------|
| **Modal** | Used in 10+ places | Medium | **CRITICAL** |
| **Button** | Used everywhere | Low | **CRITICAL** |
| **Card** | Layout foundation | Low | **HIGH** |
| **LoadingSpinner** | All async operations | Low | **HIGH** |
| **EmptyState** | Error/empty states | Low | **MEDIUM** |
| **StatusBadge** | Status display | Low | **MEDIUM** |

### Priority 2: Feature-Critical Components

#### Upload Components
| Component | Function | Test Priority |
|-----------|----------|---------------|
| **UploadZone** | Photo upload entry | **CRITICAL** |
| **UploadProgress** | Upload feedback | **HIGH** |

#### Face Components
| Component | Function | Test Priority |
|-----------|----------|---------------|
| **FaceGraph** | Complex D3 visualization | **CRITICAL** |
| **FaceCluster** | Face grouping display | **HIGH** |
| **FaceTabs** | Navigation | **MEDIUM** |
| **ClusterMergeModal** | Merge functionality | **HIGH** |

#### Search Components
| Component | Function | Test Priority |
|-----------|----------|---------------|
| **SearchBar** | Primary search interface | **CRITICAL** |
| **SearchResults** | Results display | **HIGH** |
| **SearchFilters** | Filter UI | **MEDIUM** |

### Priority 3: Settings/Configuration
| Component | Function | Test Priority |
|-----------|----------|---------------|
| **ConnectorCard** | Integration display | **MEDIUM** |
| **GooglePhotosSection** | Google Photos config | **MEDIUM** |
| **LocalFoldersSection** | Folder management | **MEDIUM** |
| **ModelsSection** | ML model config | **LOW** |

## 📝 Test Implementation Order

### Phase 1: Critical Shared Components (Day 1)
1. **Modal.svelte** - Complex interactions, slots, event handling
2. **Button.svelte** - Variants, disabled states, click handling
3. **Card.svelte** - Layout, children rendering

### Phase 2: Upload Flow (Day 1-2)
4. **UploadZone.svelte** - Drag/drop, file selection, validation
5. **UploadProgress.svelte** - Progress tracking, cancel functionality

### Phase 3: Search & Display (Day 2)
6. **SearchBar.svelte** - Input handling, debouncing, submit
7. **SearchResults.svelte** - Result rendering, pagination
8. **LoadingSpinner.svelte** - Animation, visibility states

### Phase 4: Face Management (Day 3)
9. **FaceGraph.svelte** - D3 integration, node interactions
10. **FaceCluster.svelte** - Cluster display, selection
11. **ClusterMergeModal.svelte** - Merge logic, confirmation

### Phase 5: Settings (Day 3-4)
12. **ConnectorCard.svelte** - Status display, actions
13. **FolderCard.svelte** - Folder operations
14. **GooglePhotosSection.svelte** - OAuth flow

## 🧪 Testing Strategy

### For Each Component Test:

1. **Props Testing**
   - Required props validation
   - Optional props with defaults
   - Type checking

2. **State Management**
   - Initial state
   - State transitions
   - Reactive updates ($state, $derived)

3. **User Interactions**
   - Click events
   - Form inputs
   - Keyboard navigation
   - Drag and drop (where applicable)

4. **Rendering**
   - Conditional rendering
   - Slot content (snippets in Svelte 5)
   - CSS classes based on props/state

5. **Accessibility**
   - ARIA attributes
   - Keyboard navigation
   - Screen reader compatibility

6. **Edge Cases**
   - Empty states
   - Error states
   - Loading states
   - Boundary conditions

## 📈 Success Metrics

- **Target**: 80% component test coverage
- **Critical Path Coverage**: 100% for upload, search, and face detection flows
- **Regression Prevention**: All fixed bugs get test cases

## 🚀 Quick Start Commands

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test file
npm test Modal.test.ts

# Watch mode for TDD
npm test -- --watch

# Run only component tests
npm test -- src/lib/**/components/**/*.test.ts
```

## 📋 Test Template

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, fireEvent, screen } from '@testing-library/svelte';
import ComponentName from './ComponentName.svelte';

describe('ComponentName', () => {
  describe('Props', () => {
    it('renders with required props', () => {
      // Test required props
    });

    it('applies optional props correctly', () => {
      // Test optional props with defaults
    });
  });

  describe('User Interactions', () => {
    it('handles click events', async () => {
      // Test click handling
    });

    it('updates state on input', async () => {
      // Test form inputs
    });
  });

  describe('Rendering', () => {
    it('renders children/slots correctly', () => {
      // Test snippet/slot rendering
    });

    it('applies conditional classes', () => {
      // Test dynamic CSS classes
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      // Test accessibility
    });

    it('supports keyboard navigation', async () => {
      // Test keyboard events
    });
  });

  describe('Edge Cases', () => {
    it('handles empty state', () => {
      // Test empty data
    });

    it('displays error state', () => {
      // Test error handling
    });
  });
});
```

## Next Steps

1. Start with Phase 1 (Modal, Button, Card) - these have highest impact
2. Use TDD approach - write tests first, then fix any component issues found
3. Document any bugs found during testing
4. Update this document as tests are completed