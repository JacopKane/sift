import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
export default {
	preprocess: vitePreprocess(),
	kit: {
		// Built to static files that FastAPI serves directly. No node server to run
		// alongside the Python one, and the whole app stays a single process.
		adapter: adapter({ pages: '../sift/api/static', assets: '../sift/api/static', fallback: 'index.html' })
	}
};
