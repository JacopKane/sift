<script lang="ts">
	import { onDestroy } from 'svelte';
	import { size, tokenFor, glyphFor } from '$lib/format';
	import type { BasketItem } from '$lib/types';

	let {
		items,
		total,
		onEmpty,
		onClear
	}: {
		items: BasketItem[];
		total: number;
		onEmpty: () => Promise<void>;
		onClear: () => void;
	} = $props();

	const SECONDS = 5;

	let counting = $state(0);
	let timer: ReturnType<typeof setInterval> | undefined;

	const forced = $derived(items.filter((item) => item.overridden));

	function start() {
		counting = SECONDS;
		timer = setInterval(() => {
			counting -= 1;
			if (counting <= 0) {
				stop();
				onEmpty();
			}
		}, 1000);
	}

	function stop() {
		clearInterval(timer);
		counting = 0;
	}

	onDestroy(stop);
</script>

<!--
	The countdown is the whole point of the basket being separate from the plan.
	Adding something and acting on it are different decisions, and the seconds
	between them are where you get to change your mind.
-->
<section
	class="mb-5 rounded-md border p-4"
	style="background: var(--surface); border-color: var(--edge)"
	aria-label="Basket"
>
	<div class="flex flex-wrap items-baseline justify-between gap-2">
		<h2 class="text-[11px] font-semibold tracking-[0.14em] uppercase" style="color: var(--muted)">
			Basket · {items.length}
			{items.length === 1 ? 'item' : 'items'}
		</h2>
		<span class="font-mono text-sm">{size(total)}</span>
	</div>

	<ul class="mt-3 flex flex-col gap-1.5">
		{#each items as item (item.path)}
			<li class="flex items-baseline gap-2 text-[12.5px]">
				<span class="font-mono" style="color: {tokenFor(item.verdict)}" aria-hidden="true">
					{glyphFor(item.verdict)}
				</span>
				<span class="min-w-0 flex-1 truncate font-mono" title={item.path}>{item.path}</span>
				<span class="font-mono whitespace-nowrap" style="color: var(--muted)">
					{size(item.size_bytes)}
				</span>
			</li>
		{/each}
	</ul>

	{#if forced.length}
		<p class="mt-3 text-[12.5px]" style="color: var(--irreplaceable)">
			<span aria-hidden="true">✕</span>
			{forced.length}
			{forced.length === 1 ? 'item cannot' : 'items cannot'} be replaced. You overrode the warning —
			they will still be recoverable from quarantine until you empty it.
		</p>
	{/if}

	<div class="mt-4 flex flex-wrap items-center gap-2">
		{#if counting > 0}
			<button
				type="button"
				onclick={stop}
				class="rounded-md px-4 py-2 text-[13px] font-semibold"
				style="background: var(--review); color: var(--ground)"
			>
				Cancel — {counting}s
			</button>
			<span class="text-[12.5px]" style="color: var(--muted)" role="status" aria-live="assertive">
				Moving {size(total)} to quarantine in {counting}
				{counting === 1 ? 'second' : 'seconds'}. Nothing is deleted — undo puts it back.
			</span>
		{:else}
			<button
				type="button"
				onclick={start}
				disabled={!items.length}
				class="rounded-md px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
				style="background: var(--regenerable); color: var(--ground)"
			>
				Empty the basket
			</button>
			<button
				type="button"
				onclick={onClear}
				disabled={!items.length}
				class="rounded-md border px-3 py-2 text-[13px] disabled:opacity-50"
				style="border-color: var(--edge); color: var(--muted)"
			>
				Put everything back
			</button>
		{/if}
	</div>
</section>
