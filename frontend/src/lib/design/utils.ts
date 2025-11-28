/**
 * Design System Utilities
 *
 * Helper functions for working with design tokens in TypeScript and CSS.
 */

import {
	colors,
	spacing,
	typography,
	borders,
	shadows,
	transitions,
	components,
	breakpoints,
	type SpacingToken,
	type FontSizeToken
} from './tokens';

// =============================================================================
// CSS CUSTOM PROPERTIES
// =============================================================================

/**
 * Generate CSS custom properties (CSS variables) from design tokens.
 * This allows tokens to be used in CSS via var(--color-primary-600).
 *
 * @example
 * const cssVars = generateCssVariables();
 * // Apply to document root
 * Object.entries(cssVars).forEach(([key, value]) => {
 *   document.documentElement.style.setProperty(key, value);
 * });
 */
export function generateCssVariables(): Record<string, string> {
	const vars: Record<string, string> = {};

	// Colors
	Object.entries(colors).forEach(([category, shades]) => {
		if (typeof shades === 'object') {
			Object.entries(shades).forEach(([shade, value]) => {
				vars[`--color-${category}-${shade}`] = value;
			});
		}
	});

	// Spacing
	Object.entries(spacing).forEach(([size, value]) => {
		vars[`--spacing-${size}`] = value;
	});

	// Typography
	Object.entries(typography.fontSize).forEach(([size, value]) => {
		vars[`--font-size-${size}`] = value;
	});

	Object.entries(typography.fontWeight).forEach(([weight, value]) => {
		vars[`--font-weight-${weight}`] = value;
	});

	Object.entries(typography.lineHeight).forEach(([height, value]) => {
		vars[`--line-height-${height}`] = value;
	});

	// Borders
	Object.entries(borders.radius).forEach(([size, value]) => {
		vars[`--border-radius-${size}`] = value;
	});

	Object.entries(borders.width).forEach(([size, value]) => {
		vars[`--border-width-${size}`] = value;
	});

	// Shadows
	Object.entries(shadows).forEach(([size, value]) => {
		vars[`--shadow-${size}`] = value;
	});

	// Transitions
	Object.entries(transitions.duration).forEach(([speed, value]) => {
		vars[`--transition-duration-${speed}`] = value;
	});

	Object.entries(transitions.easing).forEach(([easing, value]) => {
		vars[`--transition-easing-${easing}`] = value;
	});

	return vars;
}

/**
 * Get a CSS custom property reference for a token.
 *
 * @example
 * getCssVar('color', 'primary', '600') // 'var(--color-primary-600)'
 * getCssVar('spacing', 'md') // 'var(--spacing-md)'
 */
export function getCssVar(...parts: string[]): string {
	return `var(--${parts.join('-')})`;
}

// =============================================================================
// COLOR UTILITIES
// =============================================================================

/**
 * Get a color value from the color palette.
 *
 * @example
 * getColor('primary', 600) // '#0284c7'
 * getColor('success', 500) // '#10b981'
 */
export function getColor(
	category: keyof typeof colors,
	shade: string | number
): string | undefined {
	const colorCategory = colors[category];
	if (typeof colorCategory === 'object' && shade in colorCategory) {
		return colorCategory[shade as keyof typeof colorCategory];
	}
	return undefined;
}

/**
 * Convert hex color to RGB values.
 *
 * @example
 * hexToRgb('#3b82f6') // { r: 59, g: 130, b: 246 }
 */
export function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
	const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
	if (!result) {
		return null;
	}

	// Type guard: exec result always has these indices when regex matches
	const r = result[1];
	const g = result[2];
	const b = result[3];

	if (!r || !g || !b) {
		return null;
	}

	return {
		r: parseInt(r, 16),
		g: parseInt(g, 16),
		b: parseInt(b, 16)
	};
}

/**
 * Convert hex color to RGBA string.
 *
 * @example
 * hexToRgba('#3b82f6', 0.5) // 'rgba(59, 130, 246, 0.5)'
 */
export function hexToRgba(hex: string, alpha: number): string | null {
	const rgb = hexToRgb(hex);
	return rgb ? `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})` : null;
}

/**
 * Get a color with opacity.
 *
 * @example
 * getColorWithAlpha('primary', 600, 0.5) // 'rgba(2, 132, 199, 0.5)'
 */
export function getColorWithAlpha(
	category: keyof typeof colors,
	shade: string | number,
	alpha: number
): string | null {
	const color = getColor(category, shade);
	return color ? hexToRgba(color, alpha) : null;
}

// =============================================================================
// SPACING UTILITIES
// =============================================================================

/**
 * Get a spacing value from the spacing scale.
 *
 * @example
 * getSpacing('md') // '0.75rem'
 * getSpacing('xl') // '1.5rem'
 */
export function getSpacing(size: SpacingToken): string {
	return spacing[size];
}

/**
 * Get multiple spacing values (useful for padding/margin).
 *
 * @example
 * getSpacingMultiple(['sm', 'lg']) // '0.5rem 1rem'
 * getSpacingMultiple(['xs', 'sm', 'md', 'lg']) // '0.25rem 0.5rem 0.75rem 1rem'
 */
export function getSpacingMultiple(sizes: SpacingToken[]): string {
	return sizes.map((size) => spacing[size]).join(' ');
}

/**
 * Calculate spacing value by multiplying base spacing.
 *
 * @example
 * calcSpacing('md', 2) // '1.5rem' (0.75rem * 2)
 */
export function calcSpacing(size: SpacingToken, multiplier: number): string {
	const value = parseFloat(spacing[size]);
	return `${value * multiplier}rem`;
}

// =============================================================================
// TYPOGRAPHY UTILITIES
// =============================================================================

/**
 * Get a complete typography style object.
 *
 * @example
 * getTypographyStyle('lg', 'semibold', 'normal')
 * // { fontSize: '1.125rem', fontWeight: '600', lineHeight: '1.5' }
 */
export function getTypographyStyle(
	size: FontSizeToken,
	weight?: keyof typeof typography.fontWeight,
	lineHeight?: keyof typeof typography.lineHeight
): {
	fontSize: string;
	fontWeight?: string;
	lineHeight?: string;
} {
	return {
		fontSize: typography.fontSize[size],
		...(weight && { fontWeight: typography.fontWeight[weight] }),
		...(lineHeight && { lineHeight: typography.lineHeight[lineHeight] })
	};
}

// =============================================================================
// TRANSITION UTILITIES
// =============================================================================

/**
 * Create a transition string.
 *
 * @example
 * createTransition('colors', 'normal', 'inOut')
 * // 'background-color, border-color, color, fill, stroke 200ms cubic-bezier(0.4, 0, 0.2, 1)'
 */
export function createTransition(
	property: keyof typeof transitions.property,
	duration: keyof typeof transitions.duration,
	easing?: keyof typeof transitions.easing
): string {
	const prop = transitions.property[property];
	const dur = transitions.duration[duration];
	const ease = easing ? transitions.easing[easing] : transitions.easing.inOut;

	return `${prop} ${dur} ${ease}`;
}

// =============================================================================
// RESPONSIVE UTILITIES
// =============================================================================

/**
 * Create a media query string for a breakpoint.
 *
 * @example
 * mediaQuery('md') // '@media (min-width: 48rem)'
 * mediaQuery('lg', 'max') // '@media (max-width: 64rem)'
 */
export function mediaQuery(
	breakpoint: keyof typeof breakpoints,
	type: 'min' | 'max' = 'min'
): string {
	return `@media (${type}-width: ${breakpoints[breakpoint]})`;
}

// =============================================================================
// COMPONENT STYLE BUILDERS
// =============================================================================

/**
 * Build button styles based on variant and size.
 *
 * @example
 * buildButtonStyles('primary', 'md')
 * // { padding: '0.5rem 1rem', borderRadius: '0.375rem', ... }
 */
export function buildButtonStyles(
	variant: 'primary' | 'secondary' | 'ghost',
	size: 'sm' | 'md' | 'lg'
): Record<string, string> {
	const variantStyles: Record<string, Record<string, string>> = {
		primary: {
			backgroundColor: colors.primary[600],
			color: colors.text.inverse,
			border: 'none'
		},
		secondary: {
			backgroundColor: colors.background.primary,
			color: colors.text.secondary,
			border: `${borders.width.thin} solid ${colors.border.default}`
		},
		ghost: {
			backgroundColor: 'transparent',
			color: colors.text.secondary,
			border: 'none'
		}
	};

	return {
		...variantStyles[variant],
		padding: components.button.padding[size],
		borderRadius: components.button.borderRadius,
		transition: createTransition('colors', 'normal')
	};
}

/**
 * Build card styles.
 *
 * @example
 * buildCardStyles()
 * // { padding: '1rem', borderRadius: '0.75rem', boxShadow: '...', ... }
 */
export function buildCardStyles(): Record<string, string> {
	return {
		padding: components.card.padding,
		borderRadius: components.card.borderRadius,
		boxShadow: components.card.shadow,
		backgroundColor: colors.background.card,
		border: `${borders.width.thin} solid ${colors.border.default}`
	};
}

// =============================================================================
// VALIDATION
// =============================================================================

/**
 * Check if a value is a valid token.
 *
 * @example
 * isValidToken('spacing', 'md') // true
 * isValidToken('spacing', 'invalid') // false
 */
export function isValidToken(
	category: 'spacing' | 'color' | 'fontSize' | 'shadow',
	value: string
): boolean {
	switch (category) {
		case 'spacing':
			return value in spacing;
		case 'color':
			return value in colors;
		case 'fontSize':
			return value in typography.fontSize;
		case 'shadow':
			return value in shadows;
		default:
			return false;
	}
}
