<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import Info from '@lucide/svelte/icons/info';
	import GripVertical from '@lucide/svelte/icons/grip-vertical';
	import { size, glyphFor, tokenFor, describe } from '$lib/format';
	import type { PlanItem } from '$lib/types';

	let { item, onBasket }: { item: PlanItem; onBasket?: (path: string) => void } = $props();

	let detail = $state(false);
</script>

<!--
	Draggable: the basket is a target you can throw things at, not only a button
	you press. Both work, because dragging is not discoverable on its own — which
	is what the grip on hover is for.
-->
<div
	class="group"
	role="listitem"
	draggable="true"
	ondragstart={(e) => e.dataTransfer?.setData('text/plain', item.paths[0])}
>
	<div
		class="flex items-center gap-1.5 rounded-r-md py-1.5 pr-1 pl-1.5 transition-colors group-hover:bg-[var(--raised)]"
		style="border-left: 2px solid {tokenFor(item.verdict)}"
	>
		<span
			class="-mx-1 opacity-0 transition-opacity group-hover:opacity-60"
			style="color: var(--faint)"
			aria-hidden="true"
		>
			<GripVertical size={13} />
		</span>

		<span class="font-mono text-sm" style="color: {tokenFor(item.verdict)}" aria-hidden="true">
			{glyphFor(item.verdict)}
		</span>

		<span class="min-w-0 flex-1 truncate text-[13px]" title={item.paths[0]}>
			{item.label}
			<span class="sr-only">, {describe(item.verdict)}</span>
		</span>

		<span class="tabular text-[13px] whitespace-nowrap" style="color: var(--muted)">
			{size(item.size_bytes)}
		</span>

		<button
			type="button"
			onclick={() => (detail = !detail)}
			class="rounded p-1 opacity-0 transition-opacity group-hover:opacity-100 hover:!opacity-100 focus-visible:opacity-100"
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
				class="rounded p-1 transition-colors hover:bg-[var(--hover)] hover:text-[var(--text)]"
				style="color: var(--muted)"
				aria-label="Add {item.label} to the Trash"
				title="Add to the Trash"
			>
				<Plus size={16} aria-hidden="true" />
			</button>
		{/if}
	</div>

	{#if detail}
		<div class="mb-1.5 ml-8 text-[12.5px]" style="color: var(--muted)">
			<p class="break-all">
				{item.paths.length > 1 ? `${item.paths.length} directories` : item.paths[0]}
			</p>
			{#if item.reason}<p class="mt-0.5">{item.reason}</p>{/if}
			<p class="mt-0.5 font-mono" style="color: {tokenFor(item.verdict)}">
				{item.restore}{item.restore_time ? ` · ${item.restore_time}` : ''}
			</p>
		</div>
	{/if}
</div>
