import { sveltekit } from '@sveltejs/kit/vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';
import svelteTestConfig from './svelte.config.test.js';

export default defineConfig(({ mode }) => {
	const isTest = mode === 'test' || process.env['VITEST'];

	return {
		plugins: [isTest ? svelte(svelteTestConfig) : sveltekit()],
		...(isTest
			? {
					resolve: {
						conditions: ['browser'],
						alias: {
							$lib: '/src/lib',
							$features: '/src/lib/features',
							$shared: '/src/lib/shared',
							$api: '/src/lib/api',
							'$app/navigation': '/src/lib/shared/__mocks__/$app/navigation.ts',
							'$app/stores': '/src/lib/shared/__mocks__/$app/stores.ts'
						}
					}
			  }
			: {}),
		test: {
			include: ['src/**/*.{test,spec}.{js,ts}'],
			environment: 'jsdom',
			globals: true,
			setupFiles: ['./src/lib/shared/test-setup.ts']
		},
		server: {
			port: 5173,
			host: true
		}
	};
});
