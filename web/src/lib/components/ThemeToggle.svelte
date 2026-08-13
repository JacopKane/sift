<script lang="ts">
	import { onMount } from 'svelte';
	import Sun from '@lucide/svelte/icons/sun';
	import Moon from '@lucide/svelte/icons/moon';
	import Monitor from '@lucide/svelte/icons/monitor';
	import { theme, type Theme } from '$lib/theme.svelte';

	const OPTIONS: { value: Theme; label: string; icon: typeof Sun }[] = [
		{ value: 'light', label: 'Light', icon: Sun },
		{ value: 'dark', label: 'Dark', icon: Moon },
		{ value: 'system', label: 'System', icon: Monitor }
	];

	onMount(() => theme.watchSystem());
</script>

<!--
	A radio group rather than a two-state switch: "follow the system" is a real
	third choice, and a toggle cannot express it. Arrow keys move between options
	because that is what a radio group does.
-->
<fieldset
	class="flex items-center gap-0.5 rounded-lg border p-0.5"
	style="border-color: var(--edge)"
>
	<legend class="sr-only">Colour theme</legend>
	{#each OPTIONS as option (option.value)}
		{@const active = theme.current === option.value}
		<label
			class="cursor-pointer rounded-md p-1.5 transition-colors"
			style={active
				? 'background: var(--edge); color: var(--text)'
				: 'color: var(--faint)'}
			title={option.label}
		>
			<input
				type="radio"
				name="theme"
				value={option.value}
				checked={active}
				onchange={() => theme.set(option.value)}
				class="sr-only"
			/>
			<option.icon size={15} aria-hidden="true" />
			<span class="sr-only">{option.label}</span>
		</label>
	{/each}
</fieldset>
