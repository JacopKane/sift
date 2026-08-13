<script lang="ts">
	import { size } from '$lib/format';
	import type { DuplicateReport } from '$lib/types';

	let {
		report,
		onBasket
	}: { report: DuplicateReport; onBasket: (path: string) => void } = $props();
</script>

{#if report.sets.length}
	<h2 class="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.14em] uppercase" style="color: var(--muted)">
		The same file twice · {size(report.reclaimable_bytes)} in copies
	</h2>

	<ul class="flex flex-col gap-2">
		{#each report.sets as found (found.keep)}
			<li
				class="rounded-md border border-l-2 p-3.5"
				style="background: var(--surface); border-color: var(--edge); border-left-color: var(--review)"
			>
				<div class="flex flex-wrap items-baseline gap-x-3">
					<span class="min-w-0 flex-1 font-semibold break-words">
						{found.copies.length + 1} identical files
					</span>
					<span class="font-mono text-sm whitespace-nowrap">{size(found.reclaimable_bytes)}</span>
				</div>

				<p class="mt-1.5 font-mono text-[12.5px] break-all" style="color: var(--muted)">
					keeping {found.keep}
				</p>

				{#each found.copies as copy (copy)}
					<div class="mt-1 flex flex-wrap items-baseline gap-2">
						<span class="min-w-0 flex-1 font-mono text-[12.5px] break-all" style="color: var(--muted)">
							{copy}
						</span>
						<button
							type="button"
							onclick={() => onBasket(copy)}
							class="rounded border px-2 py-0.5 text-xs"
							style="border-color: var(--edge); color: var(--text)"
						>
							Basket the copy
						</button>
					</div>
				{/each}
			</li>
		{/each}
	</ul>
{:else}
	<h2 class="mt-7 mb-2.5 text-[11px] font-semibold tracking-[0.14em] uppercase" style="color: var(--muted)">
		The same file twice
	</h2>
	<p class="text-[13px]" style="color: var(--faint)">
		Nothing here is stored twice. {report.files_read.toLocaleString()} files were opened to check.
	</p>
{/if}
