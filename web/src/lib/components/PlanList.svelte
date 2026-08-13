<script lang="ts">
	import { size, glyphFor, tokenFor, describe } from '$lib/format';
	import type { PlanItem } from '$lib/types';

	let { title, items, empty }: { title: string; items: PlanItem[]; empty: string } = $props();
</script>

<h2 class="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.14em] uppercase" style="color: var(--muted)">
	{title}
</h2>

{#if items.length === 0}
	{#if empty}
		<p class="text-[13px]" style="color: var(--faint)">{empty}</p>
	{/if}
{:else}
	<ul class="flex flex-col gap-2">
		{#each items as item (item.label + item.paths[0])}
			<li
				class="rounded-md border border-l-2 p-3.5"
				style="background: var(--surface); border-color: var(--edge); border-left-color: {tokenFor(item.verdict)}"
			>
				<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
					<span class="font-mono text-sm" style="color: {tokenFor(item.verdict)}" aria-hidden="true">
						{glyphFor(item.verdict)}
					</span>
					<span class="min-w-0 flex-1 font-semibold break-words">{item.label}</span>
					<span class="font-mono text-sm whitespace-nowrap">{size(item.size_bytes)}</span>
				</div>

				<p class="mt-1.5 text-[12.5px] break-all" style="color: var(--muted)">
					<span class="sr-only">{describe(item.verdict)}. </span>
					{item.paths.length > 1 ? `${item.paths.length} directories` : item.paths[0]}
				</p>

				{#if item.reason}
					<p class="mt-1 text-[12.5px]" style="color: var(--muted)">{item.reason}</p>
				{/if}

				<p class="mt-1 font-mono text-[12.5px]" style="color: {tokenFor(item.verdict)}">
					{item.restore}{item.restore_time ? ` · ${item.restore_time}` : ''}
				</p>
			</li>
		{/each}
	</ul>
{/if}
