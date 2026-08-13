<script lang="ts">
	import ThemeToggle from '$lib/components/ThemeToggle.svelte';
	import Sunburst, { type ChartNode } from '$lib/components/Sunburst.svelte';
	import PlanList from '$lib/components/PlanList.svelte';
	import Answer from '$lib/components/Answer.svelte';
	import { size, VERDICT } from '$lib/format';
	import type { Plan, AskResult } from '$lib/types';

	let root = $state('~/Downloads');
	let judge = $state(true);
	let surveying = $state(false);
	let status = $state('');
	let chart = $state<ChartNode | null>(null);
	let plan = $state<Plan | null>(null);
	let surveyedRoot = $state<string | null>(null);

	let prompt = $state('');
	let asking = $state(false);
	let answer = $state<AskResult | null>(null);
	let askError = $state('');

	const EXAMPLES = [
		'remove all the torrent files',
		'get rid of the disk image installers',
		'delete the small video files'
	];

	function survey(event: SubmitEvent) {
		event.preventDefault();
		surveying = true;
		answer = null;
		askError = '';
		let seen = 0;

		const stream = new EventSource(
			`/api/survey?root=${encodeURIComponent(root)}&judge=${judge}`
		);

		stream.addEventListener('directory', (e) => {
			seen += 1;
			// A large projects folder emits tens of thousands of these; repainting on
			// every one costs more than the survey does.
			if (seen % 50 === 0 || seen < 10) {
				status = `${seen.toLocaleString()} directories · ${JSON.parse(e.data).name}`;
			}
		});

		stream.addEventListener('judging', (e) => {
			status = `${seen.toLocaleString()} directories · asking about ${JSON.parse(e.data).count}…`;
		});

		stream.addEventListener('done', (e) => {
			const payload = JSON.parse(e.data);
			chart = payload.chart;
			plan = payload.plan;
			status = `${seen.toLocaleString()} directories surveyed`;
			surveyedRoot = root;
			surveying = false;
			stream.close();
		});

		stream.onerror = () => {
			status = 'Survey stopped. Check the path is readable.';
			surveying = false;
			stream.close();
		};
	}

	async function ask(event: SubmitEvent) {
		event.preventDefault();
		if (!prompt.trim()) return;
		asking = true;
		askError = '';
		answer = null;
		try {
			const res = await fetch('/api/ask', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ root: surveyedRoot, prompt })
			});
			const body = await res.json();
			if (!res.ok) throw new Error(body.detail ?? 'That did not work.');
			answer = body;
		} catch (error) {
			askError = error instanceof Error ? error.message : String(error);
		} finally {
			asking = false;
		}
	}

	const keptBack = $derived(
		plan ? plan.protected.reduce((total, item) => total + item.size_bytes, 0) : 0
	);
</script>

<header
	class="flex flex-wrap items-center gap-3 border-b px-4 py-3 sm:px-6"
	style="border-color: var(--edge)"
>
	<h1 class="font-mono text-[13px] tracking-[0.34em] uppercase whitespace-nowrap">
		<span style="color: var(--faint)">~/</span>sift
	</h1>

	<form class="flex min-w-0 flex-1 flex-wrap items-center gap-2" onsubmit={survey}>
		<label class="sr-only" for="root">Folder to survey</label>
		<input
			id="root"
			bind:value={root}
			spellcheck="false"
			class="min-w-0 flex-1 rounded-md border px-3 py-2 font-mono text-[13px]"
			style="background: var(--surface); border-color: var(--edge); color: var(--text)"
		/>
		<label class="flex items-center gap-2 text-[13px] whitespace-nowrap" style="color: var(--muted)">
			<input type="checkbox" bind:checked={judge} class="accent-[var(--regenerable)]" />
			ask the model
		</label>
		<button
			type="submit"
			disabled={surveying}
			class="rounded-md px-4 py-2 text-[13px] font-semibold disabled:opacity-50"
			style="background: var(--regenerable); color: var(--ground)"
		>
			{surveying ? 'Surveying…' : 'Survey'}
		</button>
	</form>

	<p class="font-mono text-xs whitespace-nowrap" style="color: var(--muted)" role="status">
		{status}
	</p>

	<ThemeToggle />
</header>

<main id="main" class="mx-auto grid max-w-[1240px] gap-8 px-4 py-6 sm:px-6 lg:grid-cols-[430px_minmax(0,1fr)] lg:gap-11">
	<section class="lg:sticky lg:top-6" aria-label="Disk map">
		<Sunburst tree={chart} />
		<ul class="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs" style="color: var(--muted)">
			{#each Object.entries(VERDICT) as [key, meta] (key)}
				<li class="flex items-center gap-1.5">
					<span class="inline-block size-2.5 rounded-[2px]" style="background: {meta.token}"></span>
					<span aria-hidden="true">{meta.glyph}</span>
					{meta.label}
				</li>
			{/each}
			<li class="flex items-center gap-1.5">
				<span class="inline-block size-2.5 rounded-[2px]" style="background: var(--unknown)"></span>
				not yet judged
			</li>
		</ul>
	</section>

	<section aria-label="Plan" class="min-w-0">
		{#if surveyedRoot}
			<form class="mb-3 flex flex-wrap gap-2" onsubmit={ask}>
				<label class="sr-only" for="prompt">What to remove</label>
				<input
					id="prompt"
					bind:value={prompt}
					placeholder="Tell it what to get rid of…"
					class="min-w-0 flex-1 rounded-md border px-3 py-2 text-sm"
					style="background: var(--surface); border-color: var(--edge); color: var(--text)"
				/>
				<button
					type="submit"
					disabled={asking}
					class="rounded-md border px-4 py-2 text-[13px] font-medium disabled:opacity-50"
					style="background: var(--surface); border-color: var(--edge); color: var(--text)"
				>
					{asking ? 'Looking…' : 'Ask'}
				</button>
			</form>

			<p class="mb-5 text-xs" style="color: var(--faint)">
				Try:
				{#each EXAMPLES as example, index (example)}
					<button
						type="button"
						class="underline-offset-2 hover:underline"
						style="color: var(--muted)"
						onclick={() => (prompt = example)}>{example}</button
					>{#if index < EXAMPLES.length - 1}<span aria-hidden="true"> · </span>{/if}
				{/each}
			</p>
		{/if}

		{#if askError}
			<p class="mb-5 rounded-md border px-4 py-3 text-sm" style="border-color: var(--edge); color: var(--text)" role="alert">
				{askError}
			</p>
		{/if}

		{#if answer}
			<Answer result={answer} />
		{/if}

		<dl class="flex flex-wrap gap-x-8 gap-y-3 border-b pb-4" style="border-color: var(--edge)">
			{#each [['safe to reclaim', plan?.reclaimable_bytes, 'var(--regenerable)'], ['needs you', plan?.needs_review_bytes, 'var(--review)'], ['kept back', plan ? keptBack : undefined, 'var(--irreplaceable)']] as [label, value, token] (label)}
				<div>
					<dd class="font-mono text-2xl tracking-tight" style="color: {token}">
						{value === undefined ? '—' : size(value as number)}
					</dd>
					<dt class="text-[11px] tracking-[0.1em] uppercase" style="color: var(--muted)">{label}</dt>
				</div>
			{/each}
		</dl>

		<PlanList title="Proposed" items={plan?.proposals ?? []} empty={plan ? 'Nothing here can be safely reclaimed.' : "Run a survey to see what's here."} />
		<PlanList title="Kept back" items={plan?.protected ?? []} empty={plan ? 'Nothing here needed protecting.' : ''} />
	</section>
</main>
