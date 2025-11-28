// Import from JSON instead of TypeScript to avoid module resolution issues
import tokens from './src/lib/design/tokens.json' with { type: 'json' };

/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				// Import colors from design tokens
				primary: tokens.colors.primary,
				success: tokens.colors.success,
				error: tokens.colors.error,
				warning: tokens.colors.warning,
				info: tokens.colors.info,
				gray: tokens.colors.gray
			},
			spacing: tokens.spacing,
			fontSize: tokens.typography.fontSize,
			fontWeight: tokens.typography.fontWeight,
			lineHeight: tokens.typography.lineHeight,
			fontFamily: tokens.typography.fontFamily,
			borderRadius: tokens.borders.radius,
			borderWidth: tokens.borders.width,
			boxShadow: tokens.shadows,
			animation: {
				'fade-in': 'fadeIn 0.2s ease-in-out',
				'slide-up': 'slideUp 0.3s ease-out'
			},
			keyframes: {
				fadeIn: {
					'0%': { opacity: '0' },
					'100%': { opacity: '1' }
				},
				slideUp: {
					'0%': { opacity: '0', transform: 'translateY(10px)' },
					'100%': { opacity: '1', transform: 'translateY(0)' }
				}
			}
		}
	},
	plugins: []
};
