import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/vite-plugin-svelte').Options} */
const config = {
	preprocess: vitePreprocess(),
	hot: false
};

export default config;
