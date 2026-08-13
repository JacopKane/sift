<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { size } from '$lib/format';

	let {
		title,
		count,
		bytes,
		token,
		open = $bindable(true),
		children
	}: {
		title: string;
		count: number;
		bytes: number;
		token: string;
		open?: boolean;
		children: import('svelte').Snippet;
	} = $props();
</script>

<!--
	Every group is collapsible and scrolls inside itself. The alternative is one
	long page where finding out that "kept back" exists means scrolling past forty
	proposals — so you never learn it is there.
-->
<section class="rounded-lg border" style="border-color: var(--edge); background: var(--surface)">
	<h2>
		<button
			type="button"
			onclick={() => (open = !open)}
			class="flex w-full items-center gap-2 px-3.5 py-2.5 text-left"
			aria-expanded={open}
		>
			<span
				class="transition-transform"
				style="color: var(--faint); {open ? 'transform: rotate(90deg)' : ''}"
			>
				<ChevronRight size={15} aria-hidden="true" />
			</span>
			<span class="size-2 rounded-full" style="background: {token}" aria-hidden="true"></span>
			<span class="flex-1 text-[11px] font-semibold tracking-[0.14em] uppercase" style="color: var(--muted)">
				{title}
			</span>
			<span class="font-mono text-xs" style="color: var(--faint)">{count}</span>
			<span class="font-mono text-[13px]">{size(bytes)}</span>
		</button>
	</h2>

	{#if open}
		<!-- Scrolls itself, with a fade at the bottom so more content is obvious. -->
		<div class="group-scroll max-h-[46vh] overflow-y-auto px-3.5 pb-3.5">
			{@render children()}
		</div>
	{/if}
</section>

<style>
	.group-scroll {
		mask-image: linear-gradient(to bottom, black calc(100% - 24px), transparent);
		scrollbar-width: thin;
	}
</style>
