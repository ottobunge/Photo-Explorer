/**
 * Example usage of design tokens
 *
 * This file demonstrates how to use the design system in TypeScript code.
 */

import { colors, spacing, typography, borders, buildButtonStyles, getColor } from './index';

// Example 1: Using tokens directly
const primaryColor = colors.primary[600]; // '#0284c7'
const padding = spacing.md; // '0.75rem'
const fontSize = typography.fontSize.base; // '1rem'

// Example 2: Using utility functions
const successColor = getColor('success', 500); // '#10b981'

// Example 3: Building component styles
const buttonStyles = buildButtonStyles('primary', 'md');

// Example 4: Creating inline styles
const cardStyle = {
	backgroundColor: colors.background.card,
	padding: spacing.lg,
	borderRadius: borders.radius.xl,
	border: `1px solid ${colors.border.default}`
};

// Example 5: Type-safe token usage
type ButtonVariant = 'primary' | 'secondary' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

function getButtonClass(variant: ButtonVariant, size: ButtonSize): string {
	return `btn-${variant} btn-${size}`;
}

// Export for demonstration
export const examples = {
	primaryColor,
	padding,
	fontSize,
	successColor,
	buttonStyles,
	cardStyle,
	getButtonClass
};
