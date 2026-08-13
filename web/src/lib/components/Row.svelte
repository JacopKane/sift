<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import Info from '@lucide/svelte/icons/info';
	import { size, glyphFor, tokenFor, describe } from '$lib/format';
	import type { PlanItem } from '$lib/types';

	let { item, onBasket }: { item: PlanItem; onBasket?: (path: string) => void } = $props();

	let detail = $state(false);
</script>

<!--
	Draggable: the basket is a target you can throw things at, not only a button
	you press. Both work, because dragging is not discoverable on its own.
-->
<div
	class="group flex items-center gap-2 rounded-md px-2 py-1.5"
	draggable="true"
	role="listitem"
	ondragstart={(e) => e.dataTransfer?.setData('text/plain', item.paths[0])}
	style="border-left: 2px solid {tokenFor(item.verdict)}"
>
	<span class="font-mono text-sm" style="color: {tokenFor(item.verdict)}" aria-hidden="true">
		{glyphFor(item.verdict)}
	</span>

	<span class="min-w-0 flex-1 truncate text-[13px]" title={item.paths[0]}>
		{item.label}
		<span class="sr-only">, {describe(item.verdict)}</span>
	</span>

	<span class="font-mono text-[13px] whitespace-nowrap" style="color: var(--muted)">
		{size(item.size_bytes)}
	</span>

	<button
		type="button"
		onclick={() => (detail = !detail)}
		class="rounded p-1 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
		style="color: var(--faint)"
		aria-label="Why {item.label} is {describe(item.verdict)}"
		aria-expanded={detail}
	>
		<Info size={14} aria-hidden="true" />
	</button>

	{#if onBasket}
		<button
			type="button"
			onclick={() => onBasket?.(item.paths[0])}
			class="rounded p-1 transition-colors"
			style="color: var(--muted)"
			aria-label="Add {item.label} to basket"
			title="Add to basket"
		>
			<Plus size={16} aria-hidden="true" />
		</button>
	{/if}
</div>

{#if detail}
	<div class="mb-1.5 ml-8 text-[12.5px]" style="color: var(--muted)">
		<p class="break-all">{item.paths.length > 1 ? `${item.paths.length} directories` : item.paths[0]}</p>
		{#if item.reason}<p class="mt-0.5">{item.reason}</p>{/if}
		<p class="mt-0.5 font-mono" style="color: {tokenFor(item.verdict)}">
			{item.restore}{item.restore_time ? ` · ${item.restore_time}` : ''}
		</p>
	</div>
{/if}
