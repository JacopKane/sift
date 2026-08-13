import type { Verdict } from '$lib/format';

export type PlanItem = {
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
	protected: PlanItem[];
	reclaimable_bytes: number;
	needs_review_bytes: number;
	surveyed_bytes: number;
};

export type AskResult = {
	reason: string;
	selected: { path: string; name: string; size_bytes: number }[];
	refused: string[];
	total_bytes: number;
};
