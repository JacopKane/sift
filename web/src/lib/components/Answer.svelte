<script lang="ts">
	import { size } from '$lib/format';
	import type { AskResult } from '$lib/types';

	let { result }: { result: AskResult } = $props();
</script>

<div
	class="mb-5 rounded-md border border-l-2 p-4"
	style="background: var(--surface); border-color: var(--edge); border-left-color: var(--review)"
	aria-live="polite"
>
	<p>{result.reason}</p>

	{#if result.selected.length}
		<p class="mt-2.5 text-sm" style="color: var(--muted)">
			<span class="font-mono" style="color: var(--review)">{size(result.total_bytes)}</span>
			across {result.selected.length}
			{result.selected.length === 1 ? 'file' : 'files'}
		</p>
		<ol class="mt-1.5 list-decimal pl-5 font-mono text-[12.5px]" style="color: var(--muted)">
			{#each result.selected as file (file.path)}
				<li class="break-all py-0.5">{size(file.size_bytes)} · {file.name}</li>
			{/each}
		</ol>
	{/if}

	{#if result.refused.length}
		<p class="mt-2.5 text-[12.5px]" style="color: var(--irreplaceable)">
			<span aria-hidden="true">✕</span>
			{result.refused.length} protected
			{result.refused.length === 1 ? 'path was' : 'paths were'} left alone.
		</p>
	{/if}
</div>
