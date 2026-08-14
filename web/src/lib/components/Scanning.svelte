<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import { size } from '$lib/format';

	let {
		counted,
		judging,
		latest,
		bytes
	}: {
		counted: number;
		judging: number;
		latest: string;
		bytes: number;
	} = $props();
</script>

<!--
	What is happening, said while it happens. A scan of a real folder is tens of
	seconds and a whole disk is minutes, which is long enough that silence reads as
	broken — and the two phases are genuinely different work, so they are named
	differently rather than sharing one spinner.
-->
<section class="panel shrink-0 px-4 py-3.5" aria-label="Scanning">
	<div class="flex items-center gap-2.5">
		<span style="color: {judging ? 'var(--regenerable)' : 'var(--muted)'}" aria-hidden="true">
			{#if judging}
				<Sparkles size={16} />
			{:else}
				<span class="spinning inline-block"><Search size={16} /></span>
			{/if}
		</span>
		<span class="label flex-1" style="color: var(--text)">
			{judging ? `Judging ${judging} folders the rules could not name` : 'Reading folders'}
		</span>
		<span class="tabular text-[13px]">{size(bytes)}</span>
	</div>

	<p class="meta mt-1.5 truncate" title={latest}>
		{counted.toLocaleString()} folders{latest ? ` · ${latest}` : ''}
	</p>

	<!-- The shape of what is coming, so the page does not jump when it arrives. -->
	<div class="mt-3.5 flex flex-col gap-2" aria-hidden="true">
		{#each [100, 82, 64, 47, 33] as width, index (index)}
			<div class="skeleton h-[26px]" style="width: {width}%"></div>
		{/each}
	</div>
</section>
