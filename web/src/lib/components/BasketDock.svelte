<script lang="ts">
	import { onDestroy } from 'svelte';
	import Trash from '@lucide/svelte/icons/trash-2';
	import Undo from '@lucide/svelte/icons/undo-2';
	import X from '@lucide/svelte/icons/x';
	import ShoppingBasket from '@lucide/svelte/icons/shopping-basket';
	import { size, tokenFor, glyphFor } from '$lib/format';
	import type { BasketItem } from '$lib/types';

	let {
		items,
		total,
		onDrop,
		onEmpty,
		onClear,
		onUndo
	}: {
		items: BasketItem[];
		total: number;
		onDrop: (path: string) => void;
		onEmpty: () => Promise<void>;
		onClear: () => void;
		onUndo: () => Promise<void>;
	} = $props();

	const SECONDS = 5;

	let counting = $state(0);
	let over = $state(false);
	let timer: ReturnType<typeof setInterval> | undefined;

	const forced = $derived(items.filter((item) => item.overridden).length);

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
	Always on screen, even when empty. A basket you only see once something is in
	it is a basket nobody discovers — and it is also the drop target, which has to
	be visible to be aimed at.
-->
<aside
	class="flex h-full flex-col rounded-lg border transition-colors"
	style="border-color: {over ? 'var(--regenerable)' : 'var(--edge)'};
	       background: {over ? 'color-mix(in oklab, var(--regenerable) 8%, var(--surface))' : 'var(--surface)'}"
	aria-label="Basket"
	ondragover={(e) => {
		e.preventDefault();
		over = true;
	}}
	ondragleave={() => (over = false)}
	ondrop={(e) => {
		e.preventDefault();
		over = false;
		const path = e.dataTransfer?.getData('text/plain');
		if (path) onDrop(path);
	}}
>
	<div class="flex items-center gap-2 border-b px-3.5 py-2.5" style="border-color: var(--edge)">
		<ShoppingBasket size={15} aria-hidden="true" style="color: var(--muted)" />
		<span class="label flex-1">Basket</span>
		<span class="tabular text-[13px]">{size(total)}</span>
	</div>

	<div class="min-h-0 flex-1 overflow-y-auto px-2 py-2">
		{#if !items.length}
			<p class="px-1.5 py-6 text-center text-[12.5px]" style="color: var(--faint)">
				Drag things here, or press
				<span class="mx-0.5 inline-block rounded border px-1" style="border-color: var(--edge)">+</span>
				on anything below.
			</p>
		{:else}
			<ul class="flex flex-col gap-0.5">
				{#each items as item (item.path)}
					<li class="flex items-center gap-1.5 rounded px-1.5 py-1 text-[12.5px] transition-colors hover:bg-[var(--raised)]">
						<span class="font-mono" style="color: {tokenFor(item.verdict)}" aria-hidden="true">
							{glyphFor(item.verdict)}
						</span>
						<span class="min-w-0 flex-1 truncate" title={item.path}>
							{item.path.split('/').pop()}
						</span>
						<span class="tabular whitespace-nowrap" style="color: var(--faint)">
							{size(item.size_bytes)}
						</span>
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	{#if forced}
		<p class="px-3.5 pb-2 text-[12px]" style="color: var(--irreplaceable)">
			<span aria-hidden="true">✕</span>
			{forced} cannot be replaced. Quarantine keeps them until you empty it.
		</p>
	{/if}

	<div class="flex items-center gap-1.5 border-t p-2.5" style="border-color: var(--edge)">
		{#if counting > 0}
			<button
				type="button"
				onclick={stop}
				class="flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-2 text-[13px] font-semibold transition-[filter] hover:brightness-105"
				style="background: var(--review-solid); color: var(--on-bright)"
			>
				<X size={15} aria-hidden="true" />
				Cancel — {counting}s
			</button>
			<span class="sr-only" role="status" aria-live="assertive">
				Moving {size(total)} to quarantine in {counting} seconds.
			</span>
		{:else}
			<button
				type="button"
				onclick={start}
				disabled={!items.length}
				class="flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-2 text-[13px] font-semibold transition-[filter] enabled:hover:brightness-105"
				style={items.length
					? 'background: var(--regenerable-solid); color: var(--on-solid)'
					: 'background: var(--raised); color: var(--faint)'}
			>
				<Trash size={15} aria-hidden="true" />
				Empty
			</button>
			<button
				type="button"
				onclick={onClear}
				disabled={!items.length}
				class="rounded-md border p-2 transition-colors enabled:hover:bg-[var(--raised)] disabled:opacity-40"
				style="border-color: var(--edge); color: var(--muted)"
				aria-label="Take everything out of the basket"
				title="Take everything out"
			>
				<X size={15} aria-hidden="true" />
			</button>
		{/if}
		<button
			type="button"
			onclick={onUndo}
			class="rounded-md border p-2 transition-colors hover:bg-[var(--raised)]"
			style="border-color: var(--edge); color: var(--muted)"
			aria-label="Undo the last emptying"
			title="Undo"
		>
			<Undo size={15} aria-hidden="true" />
		</button>
	</div>
</aside>
