import type { Verdict } from '$lib/format';

export type PlanItem = {
	last_used: number | null;
	label: string;
	verdict: Verdict;
	size_bytes: number;
	paths: string[];
	restore: string;
	restore_time: string | null;
	rule_id: string | null;
	reason: string | null;
	excluding: string[];
};

export type Plan = {
	proposals: PlanItem[];
	irreplaceable: PlanItem[];
	reclaimable_bytes: number;
	needs_review_bytes: number;
	surveyed_bytes: number;
};

export type AskResult = {
	reason: string;
	selected: { path: string; name: string; size_bytes: number }[];
	irreplaceable: string[];
	total_bytes: number;
};

export type BasketItem = {
	path: string;
	size_bytes: number;
	verdict: Verdict;
};

export type BasketState = {
	items: BasketItem[];
	total_bytes: number;
};

export type DuplicateSet = {
	keep: string;
	copies: string[];
	size_bytes: number;
	reclaimable_bytes: number;
};

export type DuplicateReport = {
	reclaimable_bytes: number;
	files_read: number;
	sets: DuplicateSet[];
};
