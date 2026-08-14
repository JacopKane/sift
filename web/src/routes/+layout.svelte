<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<a href="#main" class="sr-only-focusable panel px-3 py-2 text-[13px]">Skip to content</a>

{@render children()}
