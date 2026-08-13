<script lang="ts">
	import { size } from '$lib/format';

	let { onDropped }: { onDropped: (payload: DroppedFolder) => Promise<void> } = $props();

	export type DroppedFolder = { name: string; files: { path: string; size_bytes: number }[] };

	const CAP = 50_000;

	let over = $state(false);
	let reading = $state(false);
	let counted = $state(0);
	let problem = $state('');

	/**
	 * Walk a dropped directory in the browser.
	 *
	 * The browser hands over contents, never absolute paths — which is fine, since
	 * relative paths are all the catalog and the chart need. No bytes are uploaded:
	 * only names and sizes go to the server.
	 */
	async function walk(entry: FileSystemDirectoryEntry, prefix: string, into: DroppedFolder) {
		const reader = entry.createReader();
		for (;;) {
			// readEntries returns at most 100 at a time and must be called until it
			// returns none. Reading once silently truncates every large folder.
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
					counted = into.files.length;
				}
			}
		}
	}

	async function dropped(event: DragEvent) {
		event.preventDefault();
		over = false;
		problem = '';

		const item = event.dataTransfer?.items?.[0];
		const entry = item?.webkitGetAsEntry?.();
		if (!entry?.isDirectory) {
			problem = 'Drop a folder rather than a single file.';
			return;
		}

		reading = true;
		counted = 0;
		const payload: DroppedFolder = { name: entry.name, files: [] };
		try {
			await walk(entry as FileSystemDirectoryEntry, '', payload);
			if (payload.files.length >= CAP) {
				problem = `Stopped at ${CAP.toLocaleString()} files. Drop a smaller folder for now.`;
			}
			await onDropped(payload);
		} catch (error) {
			problem = error instanceof Error ? error.message : String(error);
		} finally {
			reading = false;
		}
	}
</script>

<div
	role="region"
	aria-label="Drop a folder to analyse"
	class="mb-5 rounded-md border border-dashed p-5 text-center text-[13px] transition-colors"
	style="border-color: {over ? 'var(--regenerable)' : 'var(--edge)'};
	       background: {over ? 'color-mix(in oklab, var(--regenerable) 8%, transparent)' : 'transparent'};
	       color: var(--muted)"
	ondragover={(e) => {
		e.preventDefault();
		over = true;
	}}
	ondragleave={() => (over = false)}
	ondrop={dropped}
>
	{#if reading}
		<span role="status" aria-live="polite">Reading… {counted.toLocaleString()} files</span>
	{:else}
		Drop a folder here to analyse it without installing anything.
		<span class="block text-xs" style="color: var(--faint)">
			Only names and sizes are sent. File contents never leave your machine.
		</span>
	{/if}

	{#if problem}
		<p class="mt-2 text-xs" style="color: var(--review)" role="alert">{problem}</p>
	{/if}
</div>
