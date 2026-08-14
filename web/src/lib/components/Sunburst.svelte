<script lang="ts">
	import { size, tokenFor, solidFor, describe, type Verdict } from '$lib/format';

	export type ChartNode = {
		name: string;
		path: string;
		size_bytes: number;
		verdict: Verdict;
		label: string | null;
		unreadable: boolean;
		children: ChartNode[];
	};

	let { tree, root }: { tree: ChartNode | null; root?: string | null } = $props();

	type Arc = { node: ChartNode; depth: number; d: string };

	const CENTRE = 230;
	const INNER = 60;
	const RING = 36;
	const GAP = 3;

	function sweep(cx: number, cy: number, r0: number, r1: number, a0: number, a1: number) {
		const at = (r: number, a: number) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
		const wide = a1 - a0 > Math.PI ? 1 : 0;
		const [x0, y0] = at(r1, a0);
		const [x1, y1] = at(r1, a1);
		const [x2, y2] = at(r0, a1);
		const [x3, y3] = at(r0, a0);
		return `M${x0},${y0}A${r1},${r1} 0 ${wide} 1 ${x1},${y1}L${x2},${y2}A${r0},${r0} 0 ${wide} 0 ${x3},${y3}Z`;
	}

	const arcs = $derived.by(() => {
		if (!tree) return [] as Arc[];
		const out: Arc[] = [];
		const place = (node: ChartNode, depth: number, a0: number, a1: number) => {
			if (depth > 0 && a1 - a0 > 0.004) {
				const r0 = INNER + (depth - 1) * (RING + GAP);
				out.push({ node, depth, d: sweep(CENTRE, CENTRE, r0, r0 + RING, a0, a1) });
			}
			// Children can sum to less than their parent — loose files, pruned
			// slivers. Leaving that arc empty is more honest than stretching the
			// rest to fill it.
			const whole = node.size_bytes || 1;
			let a = a0;
			for (const child of node.children ?? []) {
				const width = (a1 - a0) * (child.size_bytes / whole);
				place(child, depth + 1, a, a + width);
				a += width;
			}
		};
		place(tree, 0, -Math.PI / 2, Math.PI * 1.5);
		return out;
	});

	// Crop to the rings that were actually drawn. A shallow tree in a box sized for
	// the deepest possible one is a small donut adrift in dead space.
	const depth = $derived(arcs.reduce((deepest, arc) => Math.max(deepest, arc.depth), 0));
	const radius = $derived(INNER + Math.max(depth, 1) * (RING + GAP));
	const box = $derived(
		`${CENTRE - radius} ${CENTRE - radius} ${radius * 2} ${radius * 2}`
	);

	let hovered = $state<ChartNode | null>(null);
	const shown = $derived(hovered ?? tree);
</script>

<div class="flex min-h-0 flex-col">
	<svg
		viewBox={box}
		class="mx-auto block h-auto w-full max-w-[290px] shrink-0"
		role="img"
		aria-label="Files and folders by size, coloured by what recovery would cost"
	>
		{#each arcs as arc (arc.node.path + arc.depth)}
			<path
				d={arc.d}
				fill={solidFor(arc.node.verdict)}
				fill-opacity={arc.node.verdict ? 1 - (arc.depth - 1) * 0.07 : 0.45}
				stroke="var(--ground)"
				stroke-width="1"
				tabindex="0"
				role="button"
				aria-label="{arc.node.name}, {size(arc.node.size_bytes)}, {describe(arc.node.verdict)}"
				class="cursor-pointer transition-opacity hover:opacity-70 focus-visible:opacity-70"
				onmouseenter={() => (hovered = arc.node)}
				onfocus={() => (hovered = arc.node)}
				onmouseleave={() => (hovered = null)}
				onblur={() => (hovered = null)}
			/>
		{/each}
	</svg>

	<!--
		Fixed height, always occupied. Growing a readout on hover pushes everything
		below it, so pointing at the map rearranges the page you are pointing at.
	-->
	<div class="mt-3 h-[3.4rem] shrink-0 px-0.5" aria-live="polite">
		{#if shown}
			<p class="display">{size(shown.size_bytes)}</p>
			<p class="meta mt-0.5 truncate" title={shown.path}>
				{hovered ? shown.path : (root ?? shown.name)}
			</p>
			<p class="text-[11px] leading-tight" style="color: {tokenFor(hovered?.verdict ?? null)}">
				{hovered ? describe(hovered.verdict) : ''}
			</p>
		{/if}
	</div>
</div>
