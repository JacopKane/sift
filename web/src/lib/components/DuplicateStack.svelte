<script lang="ts">
	import Copy from '@lucide/svelte/icons/copy';
	import Plus from '@lucide/svelte/icons/plus';
	import { size } from '$lib/format';
	import type { DuplicateSet } from '$lib/types';

	let { found, onBasket }: { found: DuplicateSet; onBasket: (path: string) => void } = $props();

	let open = $state(false);
	const copies = $derived(found.copies.length);
</script>

<!--
	Copies are stacked rather than listed. Five identical files are one decision,
	and printing all five is how a duplicate report becomes longer than the disk.
	The stack shows the count; hovering shows what is underneath.
-->
<div
	class="relative"
	onmouseenter={() => (open = true)}
	onmouseleave={() => (open = false)}
	role="listitem"
>
	<div class="flex items-center gap-2 rounded-md px-2 py-1.5" style="border-left: 2px solid var(--review)">
		<span class="relative flex items-center" aria-hidden="true">
			<!-- The offset edges are the "there are more underneath" cue. -->
			<span
				class="absolute size-4 rounded-[3px] border"
				style="border-color: var(--edge); transform: translate(3px, 3px)"
			></span>
			<span
				class="absolute size-4 rounded-[3px] border"
				style="border-color: var(--edge); transform: translate(1.5px, 1.5px)"
			></span>
			<Copy size={15} style="color: var(--review); position: relative" />
		</span>

		<button
			type="button"
			onclick={() => (open = !open)}
			class="min-w-0 flex-1 truncate text-left text-[13px]"
			aria-expanded={open}
		>
			{found.keep.split('/').pop()}
			<span style="color: var(--muted)"> ×{copies + 1}</span>
		</button>

		<span class="font-mono text-[13px] whitespace-nowrap" style="color: var(--review)">
			{size(found.reclaimable_bytes)}
		</span>

		<button
			type="button"
			onclick={() => found.copies.forEach(onBasket)}
			class="rounded p-1"
			style="color: var(--muted)"
			aria-label="Add {copies} {copies === 1 ? 'copy' : 'copies'} to basket, keeping the original"
			title="Basket the copies, keep the original"
		>
			<Plus size={16} aria-hidden="true" />
		</button>
	</div>

	{#if open}
		<ul class="mb-1 ml-8 text-[12px]" style="color: var(--muted)">
			<li class="truncate py-0.5" title={found.keep}>
				<span style="color: var(--regenerable)">keep</span>
				{found.keep}
			</li>
			{#each found.copies as copy (copy)}
				<li class="truncate py-0.5" title={copy}>
					<span style="color: var(--review)">copy</span>
					{copy}
				</li>
			{/each}
		</ul>
	{/if}
</div>
