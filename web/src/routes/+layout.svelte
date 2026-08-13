<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<a href="#main" class="sr-only-focusable rounded-md px-3 py-2" style="background: var(--surface); color: var(--text); border: 1px solid var(--edge)">
	Skip to content
</a>

{@render children()}
