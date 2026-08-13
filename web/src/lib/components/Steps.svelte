<script lang="ts">
	import Check from '@lucide/svelte/icons/check';

	let { current, steps }: { current: number; steps: string[] } = $props();
</script>

<!--
	Three steps rather than everything at once. A disk tool that opens on a wall of
	verdicts asks you to make a hundred decisions before you have made one.
-->
<ol class="flex items-center gap-1.5" aria-label="Progress">
	{#each steps as label, index (label)}
		{@const done = index < current}
		{@const active = index === current}
		<li class="flex items-center gap-1.5">
			<span
				class="flex size-5 items-center justify-center rounded-full text-[10px] font-semibold transition-colors"
				style={done
					? 'background: var(--regenerable); color: var(--ground)'
					: active
						? 'background: var(--text); color: var(--ground)'
						: 'background: var(--edge); color: var(--faint)'}
				aria-current={active ? 'step' : undefined}
			>
				{#if done}<Check size={12} aria-hidden="true" />{:else}{index + 1}{/if}
			</span>
			<span
				class="hidden text-[12.5px] sm:inline"
				style={active ? 'color: var(--text)' : 'color: var(--faint)'}
			>
				{label}
			</span>
			{#if index < steps.length - 1}
				<span class="mx-1 h-px w-4" style="background: var(--edge)" aria-hidden="true"></span>
			{/if}
		</li>
	{/each}
</ol>
