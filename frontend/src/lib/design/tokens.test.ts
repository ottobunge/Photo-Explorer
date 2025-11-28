import { describe, it, expect } from 'vitest';
import {
	colors,
	spacing,
	typography,
	borders,
	shadows,
	transitions,
	zIndex,
	breakpoints,
	components
} from './tokens';

describe('Design Tokens', () => {
	describe('Colors', () => {
		it('should have primary color palette', () => {
			expect(colors.primary).toBeDefined();
			expect(colors.primary[600]).toBe('#0284c7');
			expect(colors.primary[50]).toBe('#f0f9ff');
			expect(colors.primary[900]).toBe('#0c4a6e');
		});

		it('should have semantic colors', () => {
			expect(colors.success[500]).toBe('#10b981');
			expect(colors.error[500]).toBe('#ef4444');
			expect(colors.warning[500]).toBe('#f59e0b');
			expect(colors.info[500]).toBe('#3b82f6');
		});

		it('should have neutral grays', () => {
			expect(colors.gray[50]).toBe('#f9fafb');
			expect(colors.gray[500]).toBe('#6b7280');
			expect(colors.gray[900]).toBe('#111827');
		});

		it('should have semantic UI colors', () => {
			expect(colors.background.primary).toBe('#ffffff');
			expect(colors.text.primary).toBe('#111827');
			expect(colors.border.default).toBe('#e5e7eb');
		});

		it('should have all color shades from 50 to 900', () => {
			const shades = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900'] as const;
			const colorCategories = ['primary', 'success', 'error', 'warning', 'info', 'gray'] as const;

			colorCategories.forEach((category) => {
				shades.forEach((shade) => {
					const colorCategory = colors[category];
					// Type guard to ensure shade is a valid key
					const numericShade = Number(shade);
					if (
						typeof colorCategory === 'object' &&
						shade in colorCategory &&
						(numericShade === 50 ||
							numericShade === 100 ||
							numericShade === 200 ||
							numericShade === 300 ||
							numericShade === 400 ||
							numericShade === 500 ||
							numericShade === 600 ||
							numericShade === 700 ||
							numericShade === 800 ||
							numericShade === 900)
					) {
						const color = colorCategory[numericShade];
						expect(color).toBeDefined();
						expect(typeof color).toBe('string');
						expect(color).toMatch(/^#[0-9a-f]{6}$/i);
					}
				});
			});
		});
	});

	describe('Spacing', () => {
		it('should have all spacing tokens', () => {
			expect(spacing.xxs).toBe('0.125rem');
			expect(spacing.xs).toBe('0.25rem');
			expect(spacing.sm).toBe('0.5rem');
			expect(spacing.md).toBe('0.75rem');
			expect(spacing.lg).toBe('1rem');
			expect(spacing.xl).toBe('1.5rem');
			expect(spacing['2xl']).toBe('2rem');
		});

		it('should have consistent spacing scale', () => {
			const spacingValues = Object.values(spacing).map((s) => parseFloat(s));
			// Each value should be less than or equal to the next
			for (let i = 0; i < spacingValues.length - 1; i++) {
				const current = spacingValues[i];
				const next = spacingValues[i + 1];
				if (current !== undefined && next !== undefined) {
					expect(current).toBeLessThanOrEqual(next);
				}
			}
		});

		it('should use rem units', () => {
			Object.values(spacing).forEach((value) => {
				expect(value).toMatch(/rem$/);
			});
		});
	});

	describe('Typography', () => {
		it('should have font families', () => {
			expect(typography.fontFamily.sans).toBeDefined();
			expect(typography.fontFamily.mono).toBeDefined();
			expect(typography.fontFamily.sans).toContain('system-ui');
		});

		it('should have font sizes', () => {
			expect(typography.fontSize.xs).toBe('0.75rem');
			expect(typography.fontSize.base).toBe('1rem');
			expect(typography.fontSize.xl).toBe('1.25rem');
			expect(typography.fontSize['4xl']).toBe('2.25rem');
		});

		it('should have font weights', () => {
			expect(typography.fontWeight.normal).toBe('400');
			expect(typography.fontWeight.medium).toBe('500');
			expect(typography.fontWeight.semibold).toBe('600');
			expect(typography.fontWeight.bold).toBe('700');
		});

		it('should have line heights', () => {
			expect(typography.lineHeight.tight).toBe('1.25');
			expect(typography.lineHeight.normal).toBe('1.5');
			expect(typography.lineHeight.relaxed).toBe('1.75');
			expect(typography.lineHeight.loose).toBe('2');
		});

		it('should have increasing font size scale', () => {
			const sizes = ['xs', 'sm', 'base', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl', '6xl'];
			for (let i = 0; i < sizes.length - 1; i++) {
				const current = parseFloat(typography.fontSize[sizes[i] as keyof typeof typography.fontSize]);
				const next = parseFloat(typography.fontSize[sizes[i + 1] as keyof typeof typography.fontSize]);
				expect(current).toBeLessThan(next);
			}
		});
	});

	describe('Borders', () => {
		it('should have border radius tokens', () => {
			expect(borders.radius.none).toBe('0');
			expect(borders.radius.sm).toBe('0.1875rem');
			expect(borders.radius.md).toBe('0.25rem');
			expect(borders.radius.lg).toBe('0.375rem');
			expect(borders.radius.full).toBe('9999px');
		});

		it('should have border width tokens', () => {
			expect(borders.width.none).toBe('0');
			expect(borders.width.thin).toBe('1px');
			expect(borders.width.medium).toBe('2px');
			expect(borders.width.thick).toBe('4px');
		});

		it('should have increasing border radius', () => {
			const radii = ['sm', 'md', 'lg', 'xl', '2xl', '3xl'];
			for (let i = 0; i < radii.length - 1; i++) {
				const current = parseFloat(borders.radius[radii[i] as keyof typeof borders.radius]);
				const next = parseFloat(borders.radius[radii[i + 1] as keyof typeof borders.radius]);
				expect(current).toBeLessThan(next);
			}
		});
	});

	describe('Shadows', () => {
		it('should have shadow tokens', () => {
			expect(shadows.none).toBe('none');
			expect(shadows.sm).toBeDefined();
			expect(shadows.md).toBeDefined();
			expect(shadows.lg).toBeDefined();
			expect(shadows.xl).toBeDefined();
			expect(shadows.inner).toBeDefined();
		});

		it('should have valid CSS shadow values', () => {
			const shadowKeys = ['sm', 'md', 'lg', 'xl', '2xl', 'inner'] as const;
			shadowKeys.forEach((key) => {
				expect(shadows[key]).toMatch(/^(inset )?[0-9]/);
			});
		});
	});

	describe('Transitions', () => {
		it('should have duration tokens', () => {
			expect(transitions.duration.fastest).toBe('75ms');
			expect(transitions.duration.fast).toBe('150ms');
			expect(transitions.duration.normal).toBe('200ms');
			expect(transitions.duration.slow).toBe('300ms');
		});

		it('should have easing tokens', () => {
			expect(transitions.easing.linear).toBe('linear');
			expect(transitions.easing.in).toContain('cubic-bezier');
			expect(transitions.easing.out).toContain('cubic-bezier');
			expect(transitions.easing.inOut).toContain('cubic-bezier');
		});

		it('should have property tokens', () => {
			expect(transitions.property.all).toBe('all');
			expect(transitions.property.colors).toContain('background-color');
			expect(transitions.property.opacity).toBe('opacity');
		});

		it('should have increasing duration values', () => {
			const durations = ['fastest', 'fast', 'normal', 'slow', 'slower', 'slowest'];
			for (let i = 0; i < durations.length - 1; i++) {
				const current = parseInt(transitions.duration[durations[i] as keyof typeof transitions.duration]);
				const next = parseInt(transitions.duration[durations[i + 1] as keyof typeof transitions.duration]);
				expect(current).toBeLessThan(next);
			}
		});
	});

	describe('Z-Index', () => {
		it('should have z-index tokens', () => {
			expect(zIndex.dropdown).toBe(1000);
			expect(zIndex.modal).toBe(1050);
			expect(zIndex.tooltip).toBe(1070);
		});

		it('should have increasing z-index values', () => {
			const indices = ['dropdown', 'sticky', 'fixed', 'modalBackdrop', 'modal', 'popover', 'tooltip'];
			for (let i = 0; i < indices.length - 1; i++) {
				const current = zIndex[indices[i] as keyof typeof zIndex];
				const next = zIndex[indices[i + 1] as keyof typeof zIndex];
				expect(current).toBeLessThan(next);
			}
		});
	});

	describe('Breakpoints', () => {
		it('should have breakpoint tokens', () => {
			expect(breakpoints.sm).toBe('40rem');
			expect(breakpoints.md).toBe('48rem');
			expect(breakpoints.lg).toBe('64rem');
			expect(breakpoints.xl).toBe('80rem');
		});

		it('should have increasing breakpoint values', () => {
			const bps = ['sm', 'md', 'lg', 'xl', '2xl'];
			for (let i = 0; i < bps.length - 1; i++) {
				const current = parseFloat(breakpoints[bps[i] as keyof typeof breakpoints]);
				const next = parseFloat(breakpoints[bps[i + 1] as keyof typeof breakpoints]);
				expect(current).toBeLessThan(next);
			}
		});
	});

	describe('Components', () => {
		it('should have button component tokens', () => {
			expect(components.button.padding.sm).toBeDefined();
			expect(components.button.padding.md).toBeDefined();
			expect(components.button.padding.lg).toBeDefined();
			expect(components.button.borderRadius).toBeDefined();
		});

		it('should have input component tokens', () => {
			expect(components.input.padding).toBeDefined();
			expect(components.input.borderRadius).toBeDefined();
			expect(components.input.borderWidth).toBeDefined();
		});

		it('should have card component tokens', () => {
			expect(components.card.padding).toBeDefined();
			expect(components.card.borderRadius).toBeDefined();
			expect(components.card.shadow).toBeDefined();
		});

		it('should have modal component tokens', () => {
			expect(components.modal.borderRadius).toBeDefined();
			expect(components.modal.shadow).toBeDefined();
			expect(components.modal.backdropBlur).toBe('blur(4px)');
		});
	});

	describe('Token Consistency', () => {
		it('should use consistent color naming across categories', () => {
			const expectedShades = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900'];
			const colorCategories = ['primary', 'success', 'error', 'warning', 'info', 'gray'];

			colorCategories.forEach((category) => {
				const categoryColors = colors[category as keyof typeof colors];
				expectedShades.forEach((shade) => {
					expect(categoryColors).toHaveProperty(shade);
				});
			});
		});

		it('should use rem for most size-based tokens', () => {
			const remTokens = [
				...Object.values(spacing),
				...Object.values(typography.fontSize),
				...Object.values(borders.radius).filter((r) => r !== '0' && r !== '9999px')
			];

			remTokens.forEach((token) => {
				expect(token).toMatch(/rem$/);
			});
		});

		it('should have all tokens accessible', () => {
			// TypeScript enforces const at compile time
			// Verify all tokens are accessible
			expect(colors.primary[600]).toBe('#0284c7');
			expect(spacing.md).toBe('0.75rem');
			expect(typography.fontSize.base).toBe('1rem');
		});
	});
});
