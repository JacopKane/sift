<script lang="ts">
	import { onMount } from 'svelte';
	import Search from '@lucide/svelte/icons/search';
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

	let basket = $state<BasketState>({ items: [], total_bytes: 0 });
	let duplicates = $state<DuplicateReport | null>(null);

	const kept = $derived(plan ? plan.protected.reduce((t, i) => t + i.size_bytes, 0) : 0);
	const safe = $derived(plan ? plan.proposals.filter((i) => i.verdict === 'regenerable') : []);
	const undecided = $derived(plan ? plan.proposals.filter((i) => i.verdict === 'review') : []);

	const totals = $derived<Total[]>(
		plan
			? [
					{
						verdict: 'regenerable',
						title: 'Safe to reclaim',
						count: safe.length,
						bytes: plan.reclaimable_bytes
					},
					{
						verdict: 'review',
						title: 'Needs a decision',
						count: undecided.length,
						bytes: plan.needs_review_bytes
					},
					{
						verdict: 'irreplaceable',
						title: 'Kept back',
						count: plan.protected.length,
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
		stream.addEventListener('done', (e) => {
			const payload = JSON.parse(e.data);
			chart = payload.chart;
			plan = payload.plan;
			surveyedRoot = where;
			status = `${counted.toLocaleString()} folders`;
			surveying = false;
			stream.close();
		});
		stream.onerror = () => {
			problem = `Could not read ${where}. macOS may be blocking it — grant Full Disk Access to your terminal in System Settings › Privacy & Security, then try again.`;
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
		await run(prompt, false);
	}

	async function run(question: string, override: boolean) {
		if (!question.trim() || !surveyedRoot) return;
		asking = true;
		problem = '';
		answer = null;
		try {
			const res = await fetch('/api/ask', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ root: surveyedRoot, prompt: question, override })
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

	async function addToBasket(path: string, override = false): Promise<void> {
		const res = await fetch('/api/basket', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ root: surveyedRoot, path, override })
		});
		const body = await res.json();
		if (res.status === 409) {
			// Not forbidden — not yet insisted upon.
			if (confirm(`${body.detail}\n\nAdd it anyway? It goes to quarantine, not the bin.`)) {
				return addToBasket(path, true);
			}
			return;
		}
		basket = body;
		step = 2;
	}

	async function emptyBasket() {
		const res = await fetch(`/api/basket/empty?root=${encodeURIComponent(surveyedRoot ?? '')}`, {
			method: 'POST'
		});
		const body = await res.json();
		status = `moved ${size(body.freed_bytes)} to quarantine`;
		basket = { items: [], total_bytes: 0 };
	}

	async function clearBasket() {
		basket = await (await fetch('/api/basket', { method: 'DELETE' })).json();
	}

	async function undo() {
		const body = await (await fetch('/api/undo', { method: 'POST' })).json();
		status = `put ${body.restored.length} back`;
	}

	async function loadDuplicates() {
		const res = await fetch(`/api/duplicates?root=${encodeURIComponent(surveyedRoot ?? '')}`);
		if (res.ok) duplicates = await res.json();
	}

	function restart() {
		step = 0;
		plan = null;
		chart = null;
		answer = null;
		duplicates = null;
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
					<p
						class="shrink-0 rounded-lg border px-3.5 py-2.5 text-[13px]"
						style="border-color: var(--review); background: var(--review-bg); color: var(--text)"
						role="alert"
					>
						{problem}
					</p>
				{/if}

				{#if surveyedRoot}
					<form class="flex shrink-0 gap-2" onsubmit={ask}>
						<label class="sr-only" for="prompt">What to get rid of</label>
						<div class="relative flex-1">
							<span
								class="pointer-events-none absolute top-2.5 left-2.5"
								style="color: var(--faint)"
							>
								<Sparkles size={15} aria-hidden="true" />
							</span>
							<input
								id="prompt"
								bind:value={prompt}
								placeholder="delete the screenshots…"
								class="w-full rounded-lg border py-2 pr-3 pl-8 text-[13px] transition-colors"
								style="background: var(--surface); border-color: var(--edge); color: var(--text)"
							/>
						</div>
						<button
							type="submit"
							disabled={asking}
							class="rounded-lg border p-2 transition-colors hover:bg-[var(--raised)] disabled:opacity-40"
							style="border-color: var(--edge); color: var(--text)"
							aria-label={asking ? 'Thinking' : 'Ask'}
						>
							<Search size={16} aria-hidden="true" />
						</button>
					</form>
				{/if}

				{#if answer}
					<Group
						title="Answer"
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
									onclick={() => addToBasket(file.path, true)}
									class="rounded p-1 transition-colors hover:bg-[var(--hover)] hover:text-[var(--text)]"
									style="color: var(--muted)"
									aria-label="Add {file.name} to basket"
								>
									<Plus size={15} aria-hidden="true" />
								</button>
							</div>
						{/each}
						{#if answer.selected.length}
							<button
								type="button"
								onclick={() => answer?.selected.forEach((f) => addToBasket(f.path, true))}
								class="mt-1.5 flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors hover:bg-[var(--hover)]"
								style="border-color: var(--edge); color: var(--text)"
							>
								<Plus size={13} aria-hidden="true" />
								Add all {answer.selected.length}
							</button>
						{:else if answer.reason.toLowerCase().includes('protect')}
							<button
								type="button"
								onclick={() => run(prompt, true)}
								class="mt-1 rounded-md border px-2 py-1 text-xs transition-colors hover:bg-[var(--irreplaceable-bg)]"
								style="border-color: var(--edge-strong); color: var(--irreplaceable)"
							>
								I mean it — include protected
							</button>
						{/if}
					</Group>
				{/if}

				{#if plan}
					<Group
						title="Safe to reclaim"
						count={safe.length}
						bytes={plan.reclaimable_bytes}
						token="var(--regenerable-solid)"
					>
						{#each safe as item (item.label + item.paths[0])}
							<Row {item} onBasket={addToBasket} />
						{/each}
					</Group>

					<Group
						title="Needs a decision"
						count={undecided.length}
						bytes={plan.needs_review_bytes}
						token="var(--review-solid)"
						open={false}
					>
						{#each undecided as item (item.label + item.paths[0])}
							<Row {item} onBasket={addToBasket} />
						{/each}
					</Group>

					<Group
						title="Kept back"
						count={plan.protected.length}
						bytes={kept}
						token="var(--irreplaceable-solid)"
						open={false}
					>
						{#each plan.protected as item (item.label + item.paths[0])}
							<Row {item} onBasket={addToBasket} />
						{/each}
					</Group>

					{#if surveyedRoot}
						{#if duplicates}
							<Group
								title="The same file twice"
								count={duplicates.sets.length}
								bytes={duplicates.reclaimable_bytes}
								token="var(--review-solid)"
								open={false}
							>
								{#each duplicates.sets as found (found.keep)}
									<DuplicateStack {found} onBasket={addToBasket} />
								{/each}
							</Group>
						{:else}
							<button
								type="button"
								onclick={loadDuplicates}
								class="flex shrink-0 items-center justify-center gap-2 rounded-lg border border-dashed px-3 py-2.5 text-[13px] transition-colors hover:bg-[var(--raised)] hover:text-[var(--text)]"
								style="border-color: var(--edge); color: var(--muted)"
							>
								<Copy size={15} aria-hidden="true" />
								Look for the same file twice
							</button>
						{/if}
					{/if}
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
