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
	<!-- Fonts: Geist (UI) + Zen Kaku Gothic New (Japanese/CJK) + Noto Sans for all CJK -->
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Zen+Kaku+Gothic+New:wght@400;500&family=Noto+Sans+JP:wght@400;500&family=Noto+Sans+SC:wght@400;500&family=Noto+Sans+TC:wght@400;500&family=Noto+Sans+KR:wght@400;500&display=swap" rel="stylesheet" />
</svelte:head>

<div class="app-container">
	<nav class="navbar">
		<span class="logo">duojp <span class="logo-flags">🇯🇵🇨🇳🇹🇼🇰🇷🇹🇷</span></span>
		<div class="nav-controls">
			<button class="theme-toggle" onclick={toggleDarkMode} aria-label="Toggle dark mode">
				{#if darkMode}
					<span class="icon">☀️</span>
				{:else}
					<span class="icon">🌙</span>
				{/if}
			</button>
		</div>
	</nav>

	<div class="content">
		{@render children()}
	</div>
</div>

<style>
	:global(:root) {
		/* Light theme - clean and subtle */
		--bg-primary: #fafafa;
		--bg-secondary: #ffffff;
		--bg-tertiary: #f4f4f5;
		--text-primary: #18181b;
		--text-secondary: #52525b;
		--text-muted: #a1a1aa;
		--border-color: #e4e4e7;
		--border-dashed: #d4d4d8;
		--shadow-color: rgba(0, 0, 0, 0.06);
		--green-primary: #22c55e;
		--green-dark: #16a34a;
		--blue-primary: #3b82f6;
		--blue-dark: #2563eb;
		--tile-bg: #ffffff;
		--tile-border: #e4e4e7;
		--tile-shadow: #d4d4d8;
	}

	:global(:root.dark) {
		/* Dark theme - deep blacks with lighter raised surfaces */
		--bg-primary: #09090b;
		--bg-secondary: #18181b;
		--bg-tertiary: #27272a;
		--text-primary: #fafafa;
		--text-secondary: #a1a1aa;
		--text-muted: #71717a;
		--border-color: #3f3f46;
		--border-dashed: #52525b;
		--shadow-color: rgba(0, 0, 0, 0.5);
		--green-primary: #22c55e;
		--green-dark: #16a34a;
		--blue-primary: #3b82f6;
		--blue-dark: #2563eb;
		--tile-bg: #27272a;
		--tile-border: #3f3f46;
		--tile-shadow: #18181b;
	}

	:global(html, body) {
		margin: 0;
		padding: 0;
		height: 100%;
	}

	:global(body) {
		font-family: 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		background: var(--bg-primary);
		color: var(--text-primary);
		transition: background-color 0.2s, color 0.2s;
		overflow: hidden;
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
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
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.logo-flags {
		font-size: 1rem;
		letter-spacing: 0.1rem;
	}

	.nav-controls {
		display: flex;
		align-items: center;
		gap: 0.75rem;
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
