<script lang="ts">
	import { VERDICT } from '$lib/format';
</script>

<!--
	One per line rather than wrapped. Three items that wrap to two-then-one look
	like a mistake at every width where it happens, and there is room for a column.
-->
<ul class="mt-1 flex flex-col gap-1 text-[11.5px]" style="color: var(--muted)">
	{#each Object.entries(VERDICT) as [key, meta] (key)}
		<li class="flex items-center gap-2">
			<span class="size-2 shrink-0 rounded-full" style="background: {meta.token}"></span>
			<span class="w-3 shrink-0 text-center font-mono" style="color: {meta.token}" aria-hidden="true">
				{meta.glyph}
			</span>
			<span>{meta.label}</span>
		</li>
	{/each}
	<li class="flex items-center gap-2">
		<span class="size-2 shrink-0 rounded-full" style="background: var(--unknown)"></span>
		<span class="w-3 shrink-0 text-center font-mono" aria-hidden="true">·</span>
		<span>not yet judged</span>
	</li>
</ul>
