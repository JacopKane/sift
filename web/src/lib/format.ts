export type Verdict = 'regenerable' | 'review' | 'irreplaceable' | null;

/**
 * Colour is never the only carrier — each verdict has its own glyph and word.
 *
 * `token` is the text step, readable on our own backgrounds. `solid` is the fill
 * step, for dots and map arcs where the colour is the whole message. Radix keeps
 * these two jobs on separate steps for a reason: a fill bright enough to read as
 * text is too loud as an area, and vice versa.
 */
export const VERDICT = {
	regenerable: {
		glyph: '↺',
		label: 'rebuilds itself',
		token: 'var(--regenerable)',
		solid: 'var(--regenerable-solid)'
	},
	review: {
		glyph: '?',
		label: 'needs a decision',
		token: 'var(--review)',
		solid: 'var(--review-solid)'
	},
	irreplaceable: {
		glyph: '✕',
		label: "can't be replaced",
		token: 'var(--irreplaceable)',
		solid: 'var(--irreplaceable-solid)'
	}
} as const;

export function tokenFor(verdict: Verdict): string {
	return verdict ? VERDICT[verdict].token : 'var(--unknown)';
}

export function solidFor(verdict: Verdict): string {
	return verdict ? VERDICT[verdict].solid : 'var(--unknown)';
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

/**
 * How long ago, in words.
 *
 * "3 years ago" settles an argument a date never does — nobody subtracts
 * 2022-11-04 from today in their head while deciding whether to delete something.
 */
export function ago(when: number | null): string {
	if (!when) return '';
	const days = Math.max(Math.floor((Date.now() / 1000 - when) / 86_400), 0);
	if (days < 1) return 'today';
	if (days < 14) return `${days}d ago`;
	if (days < 60) return `${Math.floor(days / 7)}w ago`;
	if (days < 730) return `${Math.floor(days / 30)}mo ago`;
	return `${Math.floor(days / 365)}y ago`;
}

/** True once something is old enough that its age is the point. */
export function stale(when: number | null): boolean {
	return !!when && Date.now() / 1000 - when > 365 * 86_400;
}
