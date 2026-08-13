import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		// The dev server proxies to the FastAPI app, so the browser talks to one
		// origin and SSE works without CORS.
		proxy: { '/api': 'http://127.0.0.1:8765' }
	}
});
