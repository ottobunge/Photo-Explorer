import type { Preview } from '@storybook/sveltekit';
import '../src/app.css';

const preview: Preview = {
	parameters: {
		controls: {
			matchers: {
				color: /(background|color)$/i,
				date: /Date$/i
			}
		},

		a11y: {
			// 'todo' - show a11y violations in the test UI only
			// 'error' - fail CI on a11y violations
			// 'off' - skip a11y checks entirely
			test: 'todo'
		},

		backgrounds: {
			default: 'light',
			values: [
				{ name: 'light', value: '#ffffff' },
				{ name: 'dark', value: '#1f2937' },
				{ name: 'gray', value: '#f9fafb' }
			]
		},

		viewport: {
			viewports: {
				mobile: {
					name: 'Mobile',
					styles: { width: '375px', height: '667px' }
				},
				tablet: {
					name: 'Tablet',
					styles: { width: '768px', height: '1024px' }
				},
				desktop: {
					name: 'Desktop',
					styles: { width: '1280px', height: '800px' }
				}
			}
		}
	}
};

export default preview;
