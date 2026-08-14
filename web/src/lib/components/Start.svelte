<script lang="ts">
	import FolderOpen from '@lucide/svelte/icons/folder-open';
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import Download from '@lucide/svelte/icons/download';
	import Monitor from '@lucide/svelte/icons/monitor';

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

	const SHORTCUTS = [
		{ label: 'Downloads', path: '~/Downloads', icon: Download },
		{ label: 'Desktop', path: '~/Desktop', icon: Monitor },
		{ label: 'Whole disk', path: '/', icon: HardDrive }
	];

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
				<p class="display">Drop a folder here</p>
				<p class="mt-1.5 text-[13px]" style="color: var(--muted)">
					Nothing is uploaded — only names and sizes are read.
				</p>
			</div>
		{/if}

		<div class="mt-2 flex flex-wrap items-center justify-center gap-2">
			{#each SHORTCUTS as shortcut (shortcut.path)}
				<button
					type="button"
					onclick={() => onPick(shortcut.path)}
					class="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[13px] transition-colors hover:bg-[var(--raised)]"
					style="border-color: var(--edge); color: var(--text)"
				>
					<shortcut.icon size={14} aria-hidden="true" />
					{shortcut.label}
				</button>
			{/each}
		</div>

		{#if problem}
			<p class="text-xs" style="color: var(--review)" role="alert">{problem}</p>
		{/if}
	</div>
</div>
