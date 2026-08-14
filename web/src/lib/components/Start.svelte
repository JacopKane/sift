<script lang="ts">
	import { onMount } from 'svelte';
	import FolderOpen from '@lucide/svelte/icons/folder-open';
	import Download from '@lucide/svelte/icons/download';
	import Monitor from '@lucide/svelte/icons/monitor';
	import FileText from '@lucide/svelte/icons/file-text';
	import Image from '@lucide/svelte/icons/image';
	import LayoutGrid from '@lucide/svelte/icons/layout-grid';
	import Folder from '@lucide/svelte/icons/folder';

	let {
		onDropped,
		onPick,
		reading,
		counted
	}: {
		onDropped: (payload: { name: string; files: { path: string; size_bytes: number }[] }) => Promise<void>;
		onPick: (path: string) => void;
		reading: boolean;
		counted: number;
	} = $props();

	const CAP = 50_000;

	let over = $state(false);
	let problem = $state('');
	let read = $state(0);

	type Place = { label: string; path: string; icon: string };

	// Which folders exist and what this platform calls them is a question about
	// the machine, so the machine answers it. Hard-coded here it would be right
	// on macOS and quietly wrong everywhere else.
	const ICONS: Record<string, typeof Folder> = {
		download: Download,
		monitor: Monitor,
		'file-text': FileText,
		image: Image,
		'layout-grid': LayoutGrid
	};

	let places = $state<Place[]>([]);

	onMount(async () => {
		const res = await fetch('/api/places');
		if (res.ok) places = (await res.json()).places;
	});

	async function walk(
		entry: FileSystemDirectoryEntry,
		prefix: string,
		into: { name: string; files: { path: string; size_bytes: number }[] }
	) {
		const reader = entry.createReader();
		for (;;) {
			// readEntries yields at most 100 and must be called until it returns
			// none. Reading once silently truncates every large folder.
			const batch: FileSystemEntry[] = await new Promise((resolve, reject) =>
				reader.readEntries(resolve, reject)
			);
			if (!batch.length) return;
			for (const child of batch) {
				if (into.files.length >= CAP) return;
				const path = prefix ? `${prefix}/${child.name}` : child.name;
				if (child.isDirectory) {
					await walk(child as FileSystemDirectoryEntry, path, into);
				} else {
					const file: File = await new Promise((resolve, reject) =>
						(child as FileSystemFileEntry).file(resolve, reject)
					);
					into.files.push({ path, size_bytes: file.size });
					read = into.files.length;
				}
			}
		}
	}

	async function dropped(event: DragEvent) {
		event.preventDefault();
		over = false;
		problem = '';
		const entry = event.dataTransfer?.items?.[0]?.webkitGetAsEntry?.();
		if (!entry?.isDirectory) {
			problem = 'Drop a folder rather than a single file.';
			return;
		}
		const payload = { name: entry.name, files: [] as { path: string; size_bytes: number }[] };
		try {
			await walk(entry as FileSystemDirectoryEntry, '', payload);
			await onDropped(payload);
		} catch (error) {
			problem = error instanceof Error ? error.message : String(error);
		}
	}
</script>

<!--
	Fills whatever the header left over, rather than claiming a viewport height of
	its own. `100vh` minus a guess at the header is a guess that is wrong at every
	width where the header wraps, and the page grows a scrollbar over nothing.
-->
<div class="scroller flex min-h-0 flex-1 flex-col items-center justify-center px-4 py-8">
	<div
		role="region"
		aria-label="Drop a folder to analyse"
		class="flex w-full max-w-xl flex-col items-center gap-4 rounded-2xl border-2 border-dashed px-8 py-14 text-center transition-colors"
		style="border-color: {over ? 'var(--regenerable)' : 'var(--edge)'};
		       background: {over
			? 'color-mix(in oklab, var(--regenerable) 8%, transparent)'
			: 'var(--surface)'}"
		ondragover={(e) => {
			e.preventDefault();
			over = true;
		}}
		ondragleave={() => (over = false)}
		ondrop={dropped}
	>
		<span
			class="flex size-14 items-center justify-center rounded-full transition-colors"
			style="background: {over ? 'var(--regenerable-bg)' : 'var(--raised)'};
			       color: {over ? 'var(--regenerable)' : 'var(--faint)'}"
		>
			<FolderOpen size={26} aria-hidden="true" />
		</span>

		{#if reading || read}
			<p class="display" role="status" aria-live="polite">
				Reading {(counted || read).toLocaleString()} files
			</p>
		{:else}
			<div>
				<p class="display">Where should I look?</p>
				<p class="mt-1.5 text-[13px]" style="color: var(--muted)">
					Pick one, or drop any folder here. Nothing is uploaded — only names and
					sizes are read.
				</p>
			</div>
		{/if}

		<!--
			The places are the answer to the question above them, so they are the
			thing on this screen — full-width targets rather than chips under a
			heading. The whole disk is not among them on purpose: it is forty
			seconds behind a permission dialog, fine to ask for with `sift /` and a
			poor first impression to leave under the cursor.
		-->
		<div class="mt-1 grid w-full max-w-sm gap-2">
			{#each places as place (place.path)}
				{@const Icon = ICONS[place.icon] ?? Folder}
				<button
					type="button"
					onclick={() => onPick(place.path)}
					disabled={reading}
					class="flex items-center gap-3 rounded-xl border px-4 py-3 text-left text-[14px] transition-colors hover:border-[var(--edge-strong)] hover:bg-[var(--raised)] disabled:opacity-50"
					style="border-color: var(--edge); background: var(--surface); color: var(--text)"
				>
					<Icon size={18} aria-hidden="true" style="color: var(--muted)" />
					<span class="flex-1 font-medium">{place.label}</span>
					<span class="meta truncate">{place.path.replace(/^\/Users\/[^/]+/, '~')}</span>
				</button>
			{/each}
		</div>

		{#if problem}
			<p class="text-xs" style="color: var(--review)" role="alert">{problem}</p>
		{/if}
	</div>
</div>
