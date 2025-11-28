/**
 * Design System
 *
 * Centralized design tokens and utilities for the Photo Explorer application.
 *
 * @example
 * import { colors, spacing, typography } from '$lib/design';
 * import { getColor, buildButtonStyles } from '$lib/design';
 */

// Export all tokens
export * from './tokens';

// Export all utilities
export * from './utils';

// Re-export for convenience
export { colors, spacing, typography, borders, shadows, transitions, components } from './tokens';
