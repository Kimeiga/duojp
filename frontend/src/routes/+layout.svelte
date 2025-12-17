<script lang="ts">
	import { browser } from '$app/environment';

	let { children } = $props();

	// Initialize dark mode from localStorage or system preference
	let darkMode = $state(false);

	$effect(() => {
		if (browser) {
			const stored = localStorage.getItem('darkMode');
			if (stored !== null) {
				darkMode = stored === 'true';
			} else {
				darkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
			}
		}
	});

	$effect(() => {
		if (browser) {
			document.documentElement.classList.toggle('dark', darkMode);
			localStorage.setItem('darkMode', String(darkMode));
		}
	});

	function toggleDarkMode() {
		darkMode = !darkMode;
	}
</script>

<svelte:head>
	<link rel="icon" href="/favicon.svg" />
</svelte:head>

<div class="app-container">
	<nav class="navbar">
		<span class="logo">🇯🇵 duojp</span>
		<button class="theme-toggle" onclick={toggleDarkMode} aria-label="Toggle dark mode">
			{#if darkMode}
				<span class="icon">☀️</span>
			{:else}
				<span class="icon">🌙</span>
			{/if}
		</button>
	</nav>

	<div class="content">
		{@render children()}
	</div>
</div>

<style>
	:global(:root) {
		--bg-primary: #f0f0f0;
		--bg-secondary: #ffffff;
		--bg-tertiary: #e8e8e8;
		--text-primary: #333333;
		--text-secondary: #777777;
		--text-muted: #aaaaaa;
		--border-color: #e5e5e5;
		--border-dashed: #cccccc;
		--shadow-color: rgba(0, 0, 0, 0.08);
		--green-primary: #58cc02;
		--green-dark: #46a302;
		--blue-primary: #1cb0f6;
		--blue-dark: #1899d6;
		--tile-bg: #ffffff;
		--tile-border: #e5e5e5;
		--tile-shadow: #e5e5e5;
	}

	:global(:root.dark) {
		--bg-primary: #1a1a2e;
		--bg-secondary: #16213e;
		--bg-tertiary: #0f3460;
		--text-primary: #e8e8e8;
		--text-secondary: #9ca3af;
		--text-muted: #6b7280;
		--border-color: #374151;
		--border-dashed: #4b5563;
		--shadow-color: rgba(0, 0, 0, 0.3);
		--green-primary: #4ade80;
		--green-dark: #22c55e;
		--blue-primary: #38bdf8;
		--blue-dark: #0ea5e9;
		--tile-bg: #1e293b;
		--tile-border: #374151;
		--tile-shadow: #0f172a;
	}

	:global(html, body) {
		margin: 0;
		padding: 0;
		height: 100%;
	}

	:global(body) {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		background: var(--bg-primary);
		color: var(--text-primary);
		transition: background-color 0.3s, color 0.3s;
		overflow: hidden;
	}

	.navbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1.5rem;
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border-color);
		flex-shrink: 0;
		z-index: 100;
	}

	.logo {
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--green-primary);
	}

	.theme-toggle {
		background: transparent;
		border: 2px solid var(--border-color);
		border-radius: 50%;
		width: 40px;
		height: 40px;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
	}

	.theme-toggle:hover {
		background: var(--bg-tertiary);
		border-color: var(--text-muted);
	}

	.icon {
		font-size: 1.2rem;
	}

	.app-container {
		display: flex;
		flex-direction: column;
		height: 100vh;
		height: 100dvh;
	}

	.content {
		flex: 1;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
	}
</style>
