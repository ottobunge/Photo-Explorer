/**
 * Design System Tokens
 *
 * Centralized design tokens for colors, spacing, typography, and other
 * design primitives to ensure consistency across the application.
 *
 * These tokens are compatible with both CSS-in-JS and Tailwind approaches.
 */

// =============================================================================
// COLORS
// =============================================================================

export const colors = {
	// Primary palette - Blues (main brand color)
	primary: {
		50: '#f0f9ff',
		100: '#e0f2fe',
		200: '#bae6fd',
		300: '#7dd3fc',
		400: '#38bdf8',
		500: '#0ea5e9',
		600: '#0284c7', // Main primary
		700: '#0369a1',
		800: '#075985',
		900: '#0c4a6e',
		950: '#082f49'
	},

	// Semantic colors
	success: {
		50: '#ecfdf5',
		100: '#d1fae5',
		200: '#a7f3d0',
		300: '#6ee7b7',
		400: '#34d399',
		500: '#10b981', // Main success
		600: '#059669',
		700: '#047857',
		800: '#065f46',
		900: '#064e3b'
	},

	error: {
		50: '#fef2f2',
		100: '#fee2e2',
		200: '#fecaca',
		300: '#fca5a5',
		400: '#f87171',
		500: '#ef4444', // Main error
		600: '#dc2626',
		700: '#b91c1c',
		800: '#991b1b',
		900: '#7f1d1d'
	},

	warning: {
		50: '#fffbeb',
		100: '#fef3c7',
		200: '#fde68a',
		300: '#fcd34d',
		400: '#fbbf24',
		500: '#f59e0b', // Main warning
		600: '#d97706',
		700: '#b45309',
		800: '#92400e',
		900: '#78350f'
	},

	info: {
		50: '#eff6ff',
		100: '#dbeafe',
		200: '#bfdbfe',
		300: '#93c5fd',
		400: '#60a5fa',
		500: '#3b82f6', // Main info
		600: '#2563eb',
		700: '#1d4ed8',
		800: '#1e40af',
		900: '#1e3a8a'
	},

	// Neutral grays
	gray: {
		50: '#f9fafb',
		100: '#f3f4f6',
		200: '#e5e7eb',
		300: '#d1d5db',
		400: '#9ca3af',
		500: '#6b7280',
		600: '#4b5563',
		700: '#374151',
		800: '#1f2937',
		900: '#111827'
	},

	// Semantic UI colors (mapped to specific use cases)
	background: {
		primary: '#ffffff',
		secondary: '#f9fafb',
		tertiary: '#f3f4f6',
		card: '#ffffff',
		modal: '#ffffff'
	},

	text: {
		primary: '#111827',
		secondary: '#4b5563',
		muted: '#6b7280',
		disabled: '#9ca3af',
		inverse: '#ffffff'
	},

	border: {
		default: '#e5e7eb',
		light: '#f3f4f6',
		dark: '#d1d5db',
		focus: '#3b82f6'
	},

	// Toggle/Switch colors
	toggle: {
		off: '#ccc',
		on: '#3b82f6'
	}
} as const;

// =============================================================================
// SPACING
// =============================================================================

export const spacing = {
	/** 2px */
	xxs: '0.125rem',
	/** 4px */
	xs: '0.25rem',
	/** 8px */
	sm: '0.5rem',
	/** 12px */
	md: '0.75rem',
	/** 16px */
	lg: '1rem',
	/** 24px */
	xl: '1.5rem',
	/** 32px */
	'2xl': '2rem',
	/** 48px */
	'3xl': '3rem',
	/** 64px */
	'4xl': '4rem',
	/** 80px */
	'5xl': '5rem',
	/** 96px */
	'6xl': '6rem'
} as const;

// =============================================================================
// TYPOGRAPHY
// =============================================================================

export const typography = {
	fontFamily: {
		sans: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
		mono: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace'
	},

	fontSize: {
		/** 12px */
		xs: '0.75rem',
		/** 14px */
		sm: '0.875rem',
		/** 16px */
		base: '1rem',
		/** 18px */
		lg: '1.125rem',
		/** 20px */
		xl: '1.25rem',
		/** 24px */
		'2xl': '1.5rem',
		/** 30px */
		'3xl': '1.875rem',
		/** 36px */
		'4xl': '2.25rem',
		/** 48px */
		'5xl': '3rem',
		/** 60px */
		'6xl': '3.75rem'
	},

	fontWeight: {
		normal: '400',
		medium: '500',
		semibold: '600',
		bold: '700'
	},

	lineHeight: {
		tight: '1.25',
		normal: '1.5',
		relaxed: '1.75',
		loose: '2'
	}
} as const;

// =============================================================================
// BORDERS
// =============================================================================

export const borders = {
	radius: {
		none: '0',
		/** 3px */
		sm: '0.1875rem',
		/** 4px */
		md: '0.25rem',
		/** 6px */
		lg: '0.375rem',
		/** 8px */
		xl: '0.5rem',
		/** 12px */
		'2xl': '0.75rem',
		/** 16px */
		'3xl': '1rem',
		full: '9999px'
	},

	width: {
		none: '0',
		thin: '1px',
		medium: '2px',
		thick: '4px'
	}
} as const;

// =============================================================================
// SHADOWS
// =============================================================================

export const shadows = {
	none: 'none',
	sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
	md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
	lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
	xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
	'2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
	inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)'
} as const;

// =============================================================================
// TRANSITIONS
// =============================================================================

export const transitions = {
	duration: {
		/** 75ms */
		fastest: '75ms',
		/** 150ms */
		fast: '150ms',
		/** 200ms */
		normal: '200ms',
		/** 300ms */
		slow: '300ms',
		/** 500ms */
		slower: '500ms',
		/** 1000ms */
		slowest: '1000ms'
	},

	easing: {
		linear: 'linear',
		in: 'cubic-bezier(0.4, 0, 1, 1)',
		out: 'cubic-bezier(0, 0, 0.2, 1)',
		inOut: 'cubic-bezier(0.4, 0, 0.2, 1)'
	},

	// Common transition properties
	property: {
		all: 'all',
		colors: 'background-color, border-color, color, fill, stroke',
		opacity: 'opacity',
		shadow: 'box-shadow',
		transform: 'transform'
	}
} as const;

// =============================================================================
// Z-INDEX
// =============================================================================

export const zIndex = {
	dropdown: 1000,
	sticky: 1020,
	fixed: 1030,
	modalBackdrop: 1040,
	modal: 1050,
	popover: 1060,
	tooltip: 1070
} as const;

// =============================================================================
// BREAKPOINTS
// =============================================================================

export const breakpoints = {
	/** 640px */
	sm: '40rem',
	/** 768px */
	md: '48rem',
	/** 1024px */
	lg: '64rem',
	/** 1280px */
	xl: '80rem',
	/** 1536px */
	'2xl': '96rem'
} as const;

// =============================================================================
// COMPONENT-SPECIFIC TOKENS
// =============================================================================

export const components = {
	button: {
		padding: {
			sm: `${spacing.xs} ${spacing.md}`,
			md: `${spacing.sm} ${spacing.lg}`,
			lg: `${spacing.md} ${spacing.xl}`
		},
		borderRadius: borders.radius.lg
	},

	input: {
		padding: `${spacing.sm} ${spacing.lg}`,
		borderRadius: borders.radius.lg,
		borderWidth: borders.width.thin
	},

	card: {
		padding: spacing.lg,
		borderRadius: borders.radius['2xl'],
		shadow: shadows.sm
	},

	modal: {
		borderRadius: borders.radius.xl,
		shadow: shadows['2xl'],
		backdropBlur: 'blur(4px)'
	}
} as const;

// =============================================================================
// TYPE EXPORTS
// =============================================================================

export type ColorToken = keyof typeof colors;
export type ColorShade = keyof typeof colors.primary;
export type SpacingToken = keyof typeof spacing;
export type FontSizeToken = keyof typeof typography.fontSize;
export type FontWeightToken = keyof typeof typography.fontWeight;
export type BorderRadiusToken = keyof typeof borders.radius;
export type ShadowToken = keyof typeof shadows;
export type TransitionDurationToken = keyof typeof transitions.duration;
export type TransitionEasingToken = keyof typeof transitions.easing;
export type ZIndexToken = keyof typeof zIndex;
export type BreakpointToken = keyof typeof breakpoints;
