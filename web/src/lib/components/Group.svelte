<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { size } from '$lib/format';

	let {
		title,
		count,
		bytes,
		token,
		open = $bindable(true),
		list = true,
		children
	}: {
		title: string;
		count: number;
		bytes: number;
		token: string;
		open?: boolean;
		list?: boolean;
		children: import('svelte').Snippet;
	} = $props();

	/** About seven rows. Enough to judge a group by, short enough to see the next. */
	const PREVIEW = 250;

	let all = $state(false);
	let content = $state<HTMLElement | null>(null);
	let height = $state(0);

	$effect(() => {
		const element = content;
		if (!element) return;
		const observer = new ResizeObserver(() => (height = element.offsetHeight));
		observer.observe(element);
		height = element.offsetHeight;
		return () => observer.disconnect();
	});

	const longer = $derived(height > PREVIEW + 32);
	const clipped = $derived(longer && !all);
</script>

<!--
	Long groups are cut off and faded, not given their own scrollbar. A scroller
	inside a scroller inside a page means the wheel does something different
	depending on where the pointer happens to be, and the last row of every group
	sits one pixel above another group's first — so nothing reads as finished.
	Here the column is the only thing that scrolls; a group is either short, or
	visibly cut with a way to open it.
-->
<section class="panel shrink-0">
	<h2 class="sticky top-0 z-10">
		<button
			type="button"
			onclick={() => (open = !open)}
			class="flex w-full items-center gap-2 rounded-t-[9px] px-3.5 py-2.5 text-left transition-colors hover:bg-[var(--raised)]"
			style="background: var(--surface)"
			aria-expanded={open}
		>
			<span
				class="transition-transform duration-150"
				style="color: var(--faint); {open ? 'transform: rotate(90deg)' : ''}"
			>
				<ChevronRight size={15} aria-hidden="true" />
			</span>
			<span class="size-2 shrink-0 rounded-full" style="background: {token}" aria-hidden="true"></span>
			<span class="label flex-1">{title}</span>
			<span class="meta tabular">{count}</span>
			<span class="tabular text-[13px]">{size(bytes)}</span>
		</button>
	</h2>

	{#if open}
		<!--
			Clipped only while there is something to clip. Left on permanently it
			also cuts anything a row deliberately puts outside itself — the stack of
			duplicate copies opens downwards, and the last row's would vanish.
		-->
		<div
			class:overflow-hidden={clipped}
			class:fade-bottom={clipped}
			style={clipped ? `max-height: ${PREVIEW}px` : ''}
		>
			<div bind:this={content} class="px-3.5 pb-3" role={list ? 'list' : undefined}>
				{@render children()}
			</div>
		</div>

		{#if longer}
			<button
				type="button"
				onclick={() => (all = !all)}
				class="w-full rounded-b-[9px] border-t px-3.5 py-1.5 text-[12px] transition-colors hover:bg-[var(--raised)]"
				style="border-color: var(--edge); color: var(--muted)"
			>
				{all ? 'Show less' : `Show all ${count}`}
			</button>
		{/if}
	{/if}
</section>
