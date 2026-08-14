<script lang="ts">
	import { onMount } from 'svelte';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Copy from '@lucide/svelte/icons/copy';
	import Plus from '@lucide/svelte/icons/plus';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';

	import ThemeToggle from '$lib/components/ThemeToggle.svelte';
	import Sunburst, { type ChartNode } from '$lib/components/Sunburst.svelte';
	import Steps from '$lib/components/Steps.svelte';
	import Start from '$lib/components/Start.svelte';
	import Group from '$lib/components/Group.svelte';
	import Row from '$lib/components/Row.svelte';
	import BasketDock from '$lib/components/BasketDock.svelte';
	import DuplicateStack from '$lib/components/DuplicateStack.svelte';
	import Legend from '$lib/components/Legend.svelte';
	import Totals, { type Total } from '$lib/components/Totals.svelte';
	import { size } from '$lib/format';
	import type { Plan, AskResult, BasketState, DuplicateReport } from '$lib/types';

	const STEPS = ['Choose', 'Review', 'Reclaim'];

	let step = $state(0);
	let surveying = $state(false);
	let counted = $state(0);
	let status = $state('');
	let chart = $state<ChartNode | null>(null);
	let plan = $state<Plan | null>(null);
	let surveyedRoot = $state<string | null>(null);

	let prompt = $state('');
	let asking = $state(false);
	let answer = $state<AskResult | null>(null);
	let problem = $state('');
	let failed = $state(false);

	let basket = $state<BasketState>({ items: [], total_bytes: 0 });
	let duplicates = $state<DuplicateReport | null>(null);
	let hunting = $state(false);

	const kept = $derived(plan ? plan.irreplaceable.reduce((t, i) => t + i.size_bytes, 0) : 0);
	const safe = $derived(plan ? plan.proposals.filter((i) => i.verdict === 'regenerable') : []);
	const undecided = $derived(plan ? plan.proposals.filter((i) => i.verdict === 'review') : []);

	// Two groups: what Sift suggests, and the rest. A copy is a suggestion — it is
	// the same bytes twice and one of them rebuilds from the other — so duplicates
	// belong in the first group rather than in a fourth of their own. What needs a
	// decision and what cannot be replaced are both "not suggested"; the colour on
	// each row is what separates them, and it does that without a heading.
	const suggested = $derived(
		plan ? plan.reclaimable_bytes + (duplicates?.reclaimable_bytes ?? 0) : 0
	);
	const suggestedCount = $derived(safe.length + (duplicates?.sets.length ?? 0));
	const rest = $derived(plan ? [...undecided, ...plan.irreplaceable] : []);
	const restBytes = $derived(plan ? plan.needs_review_bytes + kept : 0);

	const totals = $derived<Total[]>(
		plan
			? [
					{
						verdict: 'regenerable',
						title: 'rebuilds itself',
						count: safe.length,
						bytes: plan.reclaimable_bytes
					},
					{
						verdict: 'review',
						title: 'needs a decision',
						count: undecided.length,
						bytes: plan.needs_review_bytes
					},
					{
						verdict: 'irreplaceable',
						title: "can't be replaced",
						count: plan.irreplaceable.length,
						bytes: kept
					}
				]
			: []
	);

	function survey(where: string) {
		step = 1;
		surveying = true;
		counted = 0;
		answer = null;
		problem = '';
		failed = false;

		const stream = new EventSource(`/api/survey?root=${encodeURIComponent(where)}&judge=true`);

		stream.addEventListener('directory', (e) => {
			counted += 1;
			if (counted % 50 === 0 || counted < 10) {
				status = `${counted.toLocaleString()} folders · ${JSON.parse(e.data).name}`;
			}
		});
		stream.addEventListener('judging', (e) => {
			status = `judging ${JSON.parse(e.data).count}…`;
		});
		// The server says why it stopped. Guessing is how a model timing out came
		// back as "macOS is blocking your Downloads folder" — a confident wrong
		// answer that sends you into System Settings for a problem you don't have.
		stream.addEventListener('failed', (e) => {
			problem = JSON.parse(e.data).reason;
			surveying = false;
			failed = true;
			stream.close();
		});
		stream.addEventListener('done', (e) => {
			const payload = JSON.parse(e.data);
			chart = payload.chart;
			plan = payload.plan;
			surveyedRoot = where;
			status = `${counted.toLocaleString()} folders`;
			// A survey that came back without the model is still a survey. Shown as
			// a notice beside the results rather than instead of them.
			problem = payload.note ?? '';
			surveying = false;
			stream.close();
		});
		stream.onerror = () => {
			if (failed) return; // already explained by the server
			problem = `Lost the connection while reading ${where}. Sift may have stopped — check the terminal it is running in.`;
			surveying = false;
			stream.close();
		};
	}

	async function analyseDropped(payload: { name: string; files: unknown[] }) {
		step = 1;
		surveying = true;
		const res = await fetch('/api/dropped', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});
		const body = await res.json();
		chart = body.chart;
		plan = body.plan;
		surveyedRoot = null;
		status = `${payload.files.length.toLocaleString()} files, read in your browser`;
		surveying = false;
	}

	async function ask(event: SubmitEvent) {
		event.preventDefault();
		if (!prompt.trim() || !surveyedRoot) return;
		asking = true;
		problem = '';
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
			problem = error instanceof Error ? error.message : String(error);
		} finally {
			asking = false;
		}
	}

	// Nothing is refused, so there is nothing to confirm here. The Trash panel is
	// the confirmation: what you picked is listed, coloured by what it costs, and
	// emptying is a separate press with a countdown you can cancel.
	async function addToBasket(path: string): Promise<void> {
		const res = await fetch('/api/basket', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ root: surveyedRoot, path })
		});
		basket = await res.json();
		step = 2;
	}

	async function emptyBasket() {
		const res = await fetch(`/api/basket/empty?root=${encodeURIComponent(surveyedRoot ?? '')}`, {
			method: 'POST'
		});
		const body = await res.json();
		if (!res.ok) {
			problem = body.detail ?? 'Nothing moved. Sift could not reach those files.';
			return;
		}
		// What moved has to leave the page with it, or a delete that worked reads
		// as one that did nothing: the row still listed, the map still drawing it.
		plan = body.plan;
		chart = body.chart;
		duplicates = null;
		basket = { items: [], total_bytes: 0 };
		status = body.refused.length
			? `moved ${size(body.freed_bytes)}, ${body.refused.length} could not move`
			: `moved ${size(body.freed_bytes)} to the Trash`;
		problem = body.refused.length ? body.refused.join('\n') : '';
	}

	async function clearBasket() {
		basket = await (await fetch('/api/basket', { method: 'DELETE' })).json();
	}

	async function undo() {
		const body = await (await fetch('/api/undo', { method: 'POST' })).json();
		status = `put ${body.restored.length} back`;
	}

	async function loadDuplicates() {
		// Every file that shares a size with another gets opened and read, so on a
		// large folder this is minutes, not moments. Saying so beats a dead button.
		hunting = true;
		try {
			const res = await fetch(`/api/duplicates?root=${encodeURIComponent(surveyedRoot ?? '')}`);
			if (res.ok) duplicates = await res.json();
		} finally {
			hunting = false;
		}
	}

	function restart() {
		step = 0;
		plan = null;
		chart = null;
		answer = null;
		duplicates = null;
		hunting = false;
		surveyedRoot = null;
		status = '';
	}

	// `sift ~/Projects` points the window at that folder. Honouring it here is
	// what makes naming a folder on the command line mean anything; without it
	// the argument is accepted, passed along, and quietly dropped.
	onMount(() => {
		const asked = new URLSearchParams(location.search).get('root');
		if (asked) survey(asked);
	});
</script>

<!--
	`dvh`, not `vh`: on iOS the address bar is part of `vh`, so a full-height app
	is always a little taller than the window and always scrolls by that much.
	Below the header there is exactly one scrolling region per column.
-->
<div class="flex h-dvh flex-col overflow-hidden">
	<header
		class="flex shrink-0 flex-wrap items-center gap-3 border-b px-4 py-2.5 sm:px-5"
		style="border-color: var(--edge)"
	>
		<h1 class="font-mono text-[13px] tracking-[0.3em] uppercase whitespace-nowrap">
			<span style="color: var(--faint)">~/</span>sift
		</h1>

		{#if step > 0}
			<button
				type="button"
				onclick={restart}
				class="rounded-md border p-1.5 transition-colors hover:bg-[var(--raised)]"
				style="border-color: var(--edge); color: var(--muted)"
				aria-label="Choose another folder"
				title="Choose another folder"
			>
				<ArrowLeft size={15} aria-hidden="true" />
			</button>
		{/if}

		<Steps current={step} steps={STEPS} />

		<span class="flex-1"></span>

		{#if status}
			<span class="meta tabular" role="status">{status}</span>
		{/if}
		<ThemeToggle />
	</header>

	{#if step === 0}
		<Start onDropped={analyseDropped} onPick={survey} reading={surveying} {counted} />
	{:else}
		<main
			id="main"
			class="grid min-h-0 flex-1 gap-4 overflow-hidden p-4 lg:grid-cols-[340px_minmax(0,1fr)_290px]"
		>
			<section class="scroller hidden min-h-0 flex-col gap-4 pr-1 lg:flex" aria-label="Disk map">
				<Sunburst tree={chart} root={surveyedRoot} />

				{#if plan}
					<div>
						<h2 class="label mb-1">Breakdown</h2>
						<Totals rows={totals} />
					</div>
				{/if}

				<div>
					<h2 class="label">Colour</h2>
					<Legend />
				</div>
			</section>

			<section class="scroller flex min-h-0 flex-col gap-3 pr-1" aria-label="What was found">
				{#if problem}
					<div
						class="flex shrink-0 items-start gap-3 rounded-lg border px-3.5 py-2.5 text-[13px]"
						style="border-color: var(--review); background: var(--review-bg); color: var(--text)"
						role="alert"
					>
						<span class="flex-1 whitespace-pre-line">{problem}</span>
						<button
							type="button"
							onclick={() => (surveyedRoot ? survey(surveyedRoot) : restart())}
							class="shrink-0 rounded-md border px-2 py-1 text-[12px] transition-colors hover:bg-[var(--hover)]"
							style="border-color: var(--edge-strong)"
						>
							Try again
						</button>
					</div>
				{/if}

				<!--
					The groups are what Sift worked out on its own; this is where you say
					what you actually want, and it is the reason the tool exists. Sized
					accordingly rather than tucked above the list as a filter box.
				-->
				{#if surveyedRoot}
					<form class="flex shrink-0 gap-2" onsubmit={ask}>
						<label class="sr-only" for="prompt">What to get rid of</label>
						<div class="relative flex-1">
							<span
								class="pointer-events-none absolute top-3 left-3"
								style="color: {asking ? 'var(--regenerable)' : 'var(--faint)'}"
							>
								<Sparkles size={17} aria-hidden="true" />
							</span>
							<input
								id="prompt"
								bind:value={prompt}
								disabled={asking}
								placeholder="delete the screenshots on my desktop…"
								class="w-full rounded-xl border py-2.5 pr-3 pl-10 text-[14px] transition-colors disabled:opacity-60"
								style="background: var(--surface); border-color: var(--edge); color: var(--text)"
							/>
						</div>
						<button
							type="submit"
							disabled={asking}
							class="rounded-xl px-4 text-[13px] font-semibold transition-[filter] enabled:hover:brightness-105 disabled:opacity-50"
							style="background: var(--regenerable-solid); color: var(--on-solid)"
						>
							{asking ? 'Thinking…' : 'Ask'}
						</button>
					</form>
				{/if}

				{#if answer}
					<Group
						title="What you asked for"
						count={answer.selected.length}
						bytes={answer.total_bytes}
						token="var(--review-solid)"
						list={false}
					>
						<p class="mb-2 text-[12.5px]" style="color: var(--muted)">{answer.reason}</p>
						{#each answer.selected as file (file.path)}
							<div
								class="flex items-center gap-2 rounded-md px-2 py-1 text-[13px] transition-colors hover:bg-[var(--raised)]"
							>
								<span class="min-w-0 flex-1 truncate" title={file.path}>{file.name}</span>
								<span class="tabular" style="color: var(--muted)">{size(file.size_bytes)}</span>
								<button
									type="button"
									onclick={() => addToBasket(file.path)}
									class="rounded p-1 transition-colors hover:bg-[var(--hover)] hover:text-[var(--text)]"
									style="color: var(--muted)"
									aria-label="Add {file.name} to the Trash"
								>
									<Plus size={15} aria-hidden="true" />
								</button>
							</div>
						{/each}
						{#if answer.selected.length}
							<button
								type="button"
								onclick={() => answer?.selected.forEach((f) => addToBasket(f.path))}
								class="mt-1.5 flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors hover:bg-[var(--hover)]"
								style="border-color: var(--edge); color: var(--text)"
							>
								<Plus size={13} aria-hidden="true" />
								Add all {answer.selected.length}
							</button>
						{/if}
						{#if answer.irreplaceable.length}
							<p class="mt-2 text-[12px]" style="color: var(--irreplaceable)">
								<span aria-hidden="true">✕</span>
								{answer.irreplaceable.length} of these cannot be replaced.
							</p>
						{/if}
					</Group>
				{/if}

				{#if plan}
					<Group
						title="Suggestions"
						count={suggestedCount}
						bytes={suggested}
						token="var(--regenerable-solid)"
					>
						{#if !safe.length && !duplicates?.sets.length}
							<p class="px-1 py-3 text-center text-[12.5px]" style="color: var(--faint)">
								Nothing here rebuilds itself. Everything found is below — or ask for
								something specific above.
							</p>
						{/if}
						{#each safe as item (item.label + item.paths[0])}
							<Row {item} onBasket={addToBasket} />
						{/each}
						{#each duplicates?.sets ?? [] as found (found.keep)}
							<DuplicateStack {found} onBasket={addToBasket} />
						{/each}

						{#snippet footer()}
							{#if surveyedRoot && !duplicates}
								<button
									type="button"
									onclick={loadDuplicates}
									disabled={hunting}
									class="flex w-full items-center justify-center gap-2 text-[12px] transition-colors hover:text-[var(--text)] disabled:opacity-50"
									style="color: var(--muted)"
								>
									<Copy size={13} aria-hidden="true" />
									{hunting
										? 'Reading files that share a size…'
										: 'Also look for duplicates'}
								</button>
							{/if}
						{/snippet}
					</Group>

					<Group
						title="Everything else"
						count={rest.length}
						bytes={restBytes}
						token="var(--edge-strong)"
						open={false}
					>
						{#each rest as item (item.label + item.paths[0])}
							<Row {item} onBasket={addToBasket} />
						{/each}
					</Group>
				{/if}
			</section>

			<div class="min-h-0">
				<BasketDock
					items={basket.items}
					total={basket.total_bytes}
					onDrop={(path) => addToBasket(path)}
					onEmpty={emptyBasket}
					onClear={clearBasket}
					onUndo={undo}
				/>
			</div>
		</main>
	{/if}
</div>
