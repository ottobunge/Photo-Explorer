import { describe, it, expect } from 'vitest';
import {
	generateCssVariables,
	getCssVar,
	getColor,
	hexToRgb,
	hexToRgba,
	getColorWithAlpha,
	getSpacing,
	getSpacingMultiple,
	calcSpacing,
	getTypographyStyle,
	createTransition,
	buildButtonStyles,
	buildCardStyles,
	isValidToken
} from './utils';
import { colors, spacing, typography, borders } from './tokens';

describe('Design System Utilities', () => {
	describe('CSS Custom Properties', () => {
		it('should generate CSS variables from tokens', () => {
			const cssVars = generateCssVariables();

			expect(cssVars).toHaveProperty('--color-primary-600');
			expect(cssVars['--color-primary-600']).toBe('#0284c7');

			expect(cssVars).toHaveProperty('--spacing-md');
			expect(cssVars['--spacing-md']).toBe('0.75rem');

			expect(cssVars).toHaveProperty('--font-size-base');
			expect(cssVars['--font-size-base']).toBe('1rem');
		});

		it('should generate variables for all color shades', () => {
			const cssVars = generateCssVariables();
			const shades = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900'];
			const categories = ['primary', 'success', 'error', 'warning', 'info', 'gray'];

			categories.forEach((category) => {
				shades.forEach((shade) => {
					expect(cssVars).toHaveProperty(`--color-${category}-${shade}`);
				});
			});
		});

		it('should create CSS var reference', () => {
			expect(getCssVar('color', 'primary', '600')).toBe('var(--color-primary-600)');
			expect(getCssVar('spacing', 'md')).toBe('var(--spacing-md)');
			expect(getCssVar('font-size', 'base')).toBe('var(--font-size-base)');
		});
	});

	describe('Color Utilities', () => {
		it('should get color value from palette', () => {
			expect(getColor('primary', 600)).toBe('#0284c7');
			expect(getColor('success', 500)).toBe('#10b981');
			expect(getColor('error', 500)).toBe('#ef4444');
		});

		it('should return undefined for invalid color', () => {
			expect(getColor('primary', 1000)).toBeUndefined();
			// @ts-expect-error - Testing invalid input
			expect(getColor('invalid', 500)).toBeUndefined();
		});

		it('should convert hex to RGB', () => {
			const rgb = hexToRgb('#3b82f6');
			expect(rgb).toEqual({ r: 59, g: 130, b: 246 });

			const rgb2 = hexToRgb('3b82f6'); // without #
			expect(rgb2).toEqual({ r: 59, g: 130, b: 246 });
		});

		it('should return null for invalid hex', () => {
			expect(hexToRgb('invalid')).toBeNull();
			expect(hexToRgb('#zzz')).toBeNull();
		});

		it('should convert hex to RGBA', () => {
			expect(hexToRgba('#3b82f6', 0.5)).toBe('rgba(59, 130, 246, 0.5)');
			expect(hexToRgba('#000000', 1)).toBe('rgba(0, 0, 0, 1)');
			expect(hexToRgba('#ffffff', 0)).toBe('rgba(255, 255, 255, 0)');
		});

		it('should get color with alpha', () => {
			const color = getColorWithAlpha('primary', 600, 0.5);
			expect(color).toBe('rgba(2, 132, 199, 0.5)');

			const color2 = getColorWithAlpha('success', 500, 0.2);
			expect(color2).toBe('rgba(16, 185, 129, 0.2)');
		});

		it('should handle invalid color with alpha', () => {
			expect(getColorWithAlpha('primary', 1000, 0.5)).toBeNull();
		});
	});

	describe('Spacing Utilities', () => {
		it('should get spacing value', () => {
			expect(getSpacing('md')).toBe('0.75rem');
			expect(getSpacing('xl')).toBe('1.5rem');
			expect(getSpacing('xs')).toBe('0.25rem');
		});

		it('should get multiple spacing values', () => {
			expect(getSpacingMultiple(['sm', 'lg'])).toBe('0.5rem 1rem');
			expect(getSpacingMultiple(['xs', 'sm', 'md', 'lg'])).toBe('0.25rem 0.5rem 0.75rem 1rem');
		});

		it('should calculate spacing with multiplier', () => {
			expect(calcSpacing('md', 2)).toBe('1.5rem');
			expect(calcSpacing('lg', 0.5)).toBe('0.5rem');
			expect(calcSpacing('xs', 4)).toBe('1rem');
		});
	});

	describe('Typography Utilities', () => {
		it('should get typography style with all properties', () => {
			const style = getTypographyStyle('lg', 'semibold', 'normal');
			expect(style).toEqual({
				fontSize: '1.125rem',
				fontWeight: '600',
				lineHeight: '1.5'
			});
		});

		it('should get typography style with only size', () => {
			const style = getTypographyStyle('base');
			expect(style).toEqual({
				fontSize: '1rem'
			});
		});

		it('should get typography style with size and weight', () => {
			const style = getTypographyStyle('xl', 'bold');
			expect(style).toEqual({
				fontSize: '1.25rem',
				fontWeight: '700'
			});
		});
	});

	describe('Transition Utilities', () => {
		it('should create transition string', () => {
			const transition = createTransition('colors', 'normal', 'inOut');
			expect(transition).toContain('background-color');
			expect(transition).toContain('200ms');
			expect(transition).toContain('cubic-bezier');
		});

		it('should create transition with default easing', () => {
			const transition = createTransition('opacity', 'fast');
			expect(transition).toContain('opacity');
			expect(transition).toContain('150ms');
			expect(transition).toContain('cubic-bezier');
		});

		it('should handle different property types', () => {
			const allTransition = createTransition('all', 'normal');
			expect(allTransition).toContain('all');

			const transformTransition = createTransition('transform', 'slow');
			expect(transformTransition).toContain('transform');
		});
	});

	describe('Component Style Builders', () => {
		it('should build primary button styles', () => {
			const styles = buildButtonStyles('primary', 'md');

			expect(styles['backgroundColor']).toBe(colors.primary[600]);
			expect(styles['color']).toBe(colors.text.inverse);
			expect(styles['padding']).toContain('rem');
			expect(styles['borderRadius']).toBe(borders.radius.lg);
			expect(styles['transition']).toBeDefined();
		});

		it('should build secondary button styles', () => {
			const styles = buildButtonStyles('secondary', 'md');

			expect(styles['backgroundColor']).toBe(colors.background.primary);
			expect(styles['color']).toBe(colors.text.secondary);
			expect(styles['border']).toContain('solid');
		});

		it('should build ghost button styles', () => {
			const styles = buildButtonStyles('ghost', 'lg');

			expect(styles['backgroundColor']).toBe('transparent');
			expect(styles['color']).toBe(colors.text.secondary);
			expect(styles['border']).toBe('none');
		});

		it('should build different button sizes', () => {
			const small = buildButtonStyles('primary', 'sm');
			const medium = buildButtonStyles('primary', 'md');
			const large = buildButtonStyles('primary', 'lg');

			expect(small['padding']).not.toBe(medium['padding']);
			expect(medium['padding']).not.toBe(large['padding']);
		});

		it('should build card styles', () => {
			const styles = buildCardStyles();

			expect(styles['padding']).toBe(spacing.lg);
			expect(styles['borderRadius']).toBe(borders.radius['2xl']);
			expect(styles['backgroundColor']).toBe(colors.background.card);
			expect(styles['boxShadow']).toBeDefined();
			expect(styles['border']).toContain('solid');
		});
	});

	describe('Validation', () => {
		it('should validate spacing tokens', () => {
			expect(isValidToken('spacing', 'md')).toBe(true);
			expect(isValidToken('spacing', 'xl')).toBe(true);
			expect(isValidToken('spacing', 'invalid')).toBe(false);
		});

		it('should validate color tokens', () => {
			expect(isValidToken('color', 'primary')).toBe(true);
			expect(isValidToken('color', 'success')).toBe(true);
			expect(isValidToken('color', 'invalid')).toBe(false);
		});

		it('should validate fontSize tokens', () => {
			expect(isValidToken('fontSize', 'base')).toBe(true);
			expect(isValidToken('fontSize', 'xl')).toBe(true);
			expect(isValidToken('fontSize', 'invalid')).toBe(false);
		});

		it('should validate shadow tokens', () => {
			expect(isValidToken('shadow', 'sm')).toBe(true);
			expect(isValidToken('shadow', 'lg')).toBe(true);
			expect(isValidToken('shadow', 'invalid')).toBe(false);
		});
	});

	describe('Edge Cases', () => {
		it('should handle hex colors with or without #', () => {
			const withHash = hexToRgb('#3b82f6');
			const withoutHash = hexToRgb('3b82f6');
			expect(withHash).toEqual(withoutHash);
		});

		it('should handle uppercase and lowercase hex', () => {
			const uppercase = hexToRgb('#3B82F6');
			const lowercase = hexToRgb('#3b82f6');
			expect(uppercase).toEqual(lowercase);
		});

		it('should handle alpha values at boundaries', () => {
			expect(hexToRgba('#000000', 0)).toBe('rgba(0, 0, 0, 0)');
			expect(hexToRgba('#ffffff', 1)).toBe('rgba(255, 255, 255, 1)');
		});

		it('should handle spacing multiplier edge cases', () => {
			expect(calcSpacing('md', 0)).toBe('0rem');
			expect(calcSpacing('lg', 1)).toBe('1rem');
		});
	});

	describe('Type Safety', () => {
		it('should only accept valid spacing tokens', () => {
			// TypeScript should catch these at compile time
			// Runtime tests verify the values
			const validKeys: (keyof typeof spacing)[] = ['xs', 'sm', 'md', 'lg', 'xl'];
			validKeys.forEach((key) => {
				expect(spacing[key]).toBeDefined();
			});
		});

		it('should only accept valid typography tokens', () => {
			const validFontSizes: (keyof typeof typography.fontSize)[] = ['xs', 'sm', 'base', 'lg', 'xl'];
			validFontSizes.forEach((key) => {
				expect(typography.fontSize[key]).toBeDefined();
			});
		});
	});

	describe('Integration Tests', () => {
		it('should generate consistent CSS variable names', () => {
			const cssVars = generateCssVariables();
			const varName = getCssVar('color', 'primary', '600');

			// The generated CSS var should match the expected format
			expect(varName).toBe('var(--color-primary-600)');
			expect(cssVars['--color-primary-600']).toBeDefined();
		});

		it('should use colors from tokens in button styles', () => {
			const primaryBtn = buildButtonStyles('primary', 'md');
			expect(primaryBtn['backgroundColor']).toBe(colors.primary[600]);

			const secondaryBtn = buildButtonStyles('secondary', 'md');
			expect(secondaryBtn['color']).toBe(colors.text.secondary);
		});

		it('should use spacing from tokens in button styles', () => {
			const styles = buildButtonStyles('primary', 'md');
			// Check that padding uses spacing tokens
			expect(styles['padding']).toContain('rem');
		});
	});
});
