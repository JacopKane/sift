export type Verdict = 'regenerable' | 'review' | 'irreplaceable' | null;

/** Colour is never the only carrier — each verdict has its own glyph and word. */
export const VERDICT = {
	regenerable: { glyph: '↺', label: 'rebuilds itself', token: 'var(--regenerable)' },
	review: { glyph: '?', label: 'needs a decision', token: 'var(--review)' },
	irreplaceable: { glyph: '✕', label: "can't be replaced", token: 'var(--irreplaceable)' }
} as const;

export function tokenFor(verdict: Verdict): string {
	return verdict ? VERDICT[verdict].token : 'var(--unknown)';
}

export function glyphFor(verdict: Verdict): string {
	return verdict ? VERDICT[verdict].glyph : '·';
}

export function describe(verdict: Verdict): string {
	return verdict ? VERDICT[verdict].label : 'not yet judged';
}

export function size(bytes: number): string {
	if (!bytes) return '0 B';
	const units = ['B', 'KB', 'MB', 'GB', 'TB'];
	let value = bytes;
	let unit = 0;
	while (value >= 1024 && unit < units.length - 1) {
		value /= 1024;
		unit += 1;
	}
	return `${unit === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unit]}`;
}
