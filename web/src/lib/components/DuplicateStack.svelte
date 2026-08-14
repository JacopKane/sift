<script lang="ts">
	import Copy from '@lucide/svelte/icons/copy';
	import Plus from '@lucide/svelte/icons/plus';
	import { size } from '$lib/format';
	import type { DuplicateSet } from '$lib/types';

	let { found, onBasket }: { found: DuplicateSet; onBasket: (path: string) => void } = $props();

	let hovering = $state(false);
	let pinned = $state(false);
	const open = $derived(hovering || pinned);
	const copies = $derived(found.copies.length);
</script>

<!--
	Copies are stacked rather than listed. Five identical files are one decision,
	and printing all five is how a duplicate report becomes longer than the disk.
	The stack shows the count; hovering shows what is underneath — as an overlay,
	because a hover that reflows the list moves the next row out from under the
	pointer that was on its way to it.
-->
<div
	class="relative"
	role="listitem"
	onmouseenter={() => (hovering = true)}
	onmouseleave={() => (hovering = false)}
>
	<div
		class="flex items-center gap-2 rounded-r-md py-1.5 pr-1 pl-2 transition-colors hover:bg-[var(--raised)]"
		style="border-left: 2px solid {open ? 'var(--review-solid)' : 'var(--review)'}"
	>
		<span class="relative flex items-center" aria-hidden="true">
			<!-- The offset edges are the "there are more underneath" cue. -->
			<span
				class="absolute size-4 rounded-[3px] border transition-transform"
				style="border-color: var(--edge-strong); transform: translate({open ? 5 : 3}px, {open
					? 5
					: 3}px)"
			></span>
			<span
				class="absolute size-4 rounded-[3px] border transition-transform"
				style="border-color: var(--edge-strong); transform: translate({open ? 2.5 : 1.5}px, {open
					? 2.5
					: 1.5}px)"
			></span>
			<Copy size={15} style="color: var(--review); position: relative" />
		</span>

		<button
			type="button"
			onclick={() => (pinned = !pinned)}
			onfocus={() => (hovering = true)}
			onblur={() => (hovering = false)}
			class="min-w-0 flex-1 truncate text-left text-[13px]"
			aria-expanded={open}
		>
			{found.keep.split('/').pop()}
			<span class="tabular" style="color: var(--muted)"> ×{copies + 1}</span>
		</button>

		<span class="tabular text-[13px] whitespace-nowrap" style="color: var(--review)">
			{size(found.reclaimable_bytes)}
		</span>

		<button
			type="button"
			onclick={() => found.copies.forEach(onBasket)}
			class="rounded p-1 transition-colors hover:bg-[var(--hover)] hover:text-[var(--text)]"
			style="color: var(--muted)"
			aria-label="Add {copies} {copies === 1 ? 'copy' : 'copies'} to the Trash, keeping the original"
			title="Trash the copies, keep the original"
		>
			<Plus size={16} aria-hidden="true" />
		</button>
	</div>

	{#if open}
		<ul
			class="panel absolute top-full right-1 left-8 z-20 px-2 py-1.5 text-[12px] shadow-lg"
			style="background: var(--raised); color: var(--muted)"
		>
			<li class="truncate py-0.5" title={found.keep}>
				<span class="mr-1.5 font-mono" style="color: var(--regenerable)">keep</span>{found.keep}
			</li>
			{#each found.copies as copy (copy)}
				<li class="truncate py-0.5" title={copy}>
					<span class="mr-1.5 font-mono" style="color: var(--review)">copy</span>{copy}
				</li>
			{/each}
		</ul>
	{/if}
</div>
