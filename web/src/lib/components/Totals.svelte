<script lang="ts">
	import { size, VERDICT, type Verdict } from '$lib/format';

	export type Total = { verdict: Exclude<Verdict, null>; title: string; count: number; bytes: number };

	let { rows }: { rows: Total[] } = $props();
</script>

<!--
	Ordered by what you can act on, not by size: what rebuilds itself, then what
	needs you, then what is off the table. Sorting these by bytes would put the
	folder you must not touch at the top of the page on most disks.
-->
<dl class="flex flex-col">
	{#each rows as row (row.verdict)}
		<div
			class="flex items-baseline gap-2 border-b py-1.5 last:border-0"
			style="border-color: var(--edge)"
		>
			<span
				class="size-2 shrink-0 translate-y-[-1px] rounded-full"
				style="background: {VERDICT[row.verdict].solid}"
				aria-hidden="true"
			></span>
			<dt class="min-w-0 flex-1 truncate text-[12.5px]" style="color: var(--muted)">
				{row.title}
			</dt>
			<dd class="meta tabular">{row.count}</dd>
			<dd class="tabular w-[4.5rem] text-right text-[13px]">{size(row.bytes)}</dd>
		</div>
	{/each}
</dl>
