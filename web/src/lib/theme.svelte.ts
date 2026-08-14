/**
 * Light, dark, or follow the system.
 *
 * Applied before first paint by an inline script in app.html, so there is no
 * flash of the wrong theme on load.
 */

export type Theme = 'light' | 'dark' | 'system';

const KEY = 'sift-theme';

function resolve(theme: Theme): 'light' | 'dark' {
	if (theme !== 'system') return theme;
	return globalThis.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function apply(theme: Theme) {
	const dark = resolve(theme) === 'dark';
	document.documentElement.classList.toggle('dark', dark);
	document.documentElement.classList.toggle('light', !dark);
	document.documentElement.style.colorScheme = resolve(theme);
}

class ThemeStore {
	current = $state<Theme>('system');

	constructor() {
		if (typeof localStorage !== 'undefined') {
			this.current = (localStorage.getItem(KEY) as Theme) ?? 'system';
		}
	}

	set(theme: Theme) {
		this.current = theme;
		localStorage.setItem(KEY, theme);
		apply(theme);
	}

	/** Follow the OS while the preference is "system", not just at load. */
	watchSystem() {
		const media = globalThis.matchMedia?.('(prefers-color-scheme: dark)');
		const onChange = () => this.current === 'system' && apply('system');
		media?.addEventListener('change', onChange);
		return () => media?.removeEventListener('change', onChange);
	}
}

export const theme = new ThemeStore();
