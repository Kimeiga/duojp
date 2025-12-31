<script lang="ts">
	import { onMount } from 'svelte';
	import { fly } from 'svelte/transition';
	import { flip } from 'svelte/animate';
	import { dndzone } from 'svelte-dnd-action';
	import { fetchUnifiedExercise, gradeUnifiedAnswer } from '$lib/api';
	import { languageStore } from '$lib/stores/language.svelte';
	import { chineseScriptStore } from '$lib/stores/chineseScript.svelte';
	import { convertChinese } from '$lib/chineseConverter';
	import { LANGUAGES, type UnifiedExercise, type TileData, type GradeResult, type ApiTile, type Language, type LanguageExercise } from '$lib/types';

	// Animation duration for flip transitions
	const FLIP_DURATION_MS = 200;

	let unifiedExercise: UnifiedExercise | null = $state(null);
	let answerTiles: TileData[] = $state([]);
	let bankTiles: TileData[] = $state([]);
	let result: GradeResult | null = $state(null);
	let loading = $state(true);

	// Store answer/bank state per language (ja, zh, ko, tr)
	// For Chinese, both simplified and traditional share the same 'zh' state
	type LanguageState = { answerTiles: TileData[]; bankTiles: TileData[] };
	let languageStates: Record<Language, LanguageState | null> = $state({
		ja: null,
		zh: null,
		ko: null,
		tr: null
	});

	// Get available languages for this exercise (used in template)
	const availableLanguages = $derived.by(() => {
		if (!unifiedExercise) return LANGUAGES;
		return LANGUAGES.filter(l => unifiedExercise!.exercises[l.code]);
	});

	// Get current language exercise
	const currentExercise: LanguageExercise | null = $derived.by(() => {
		if (!unifiedExercise) return null;
		return unifiedExercise.exercises[languageStore.value] ?? null;
	});

	// Helper to convert text for display (Chinese conversion, Korean allomorph styling)
	function displayText(text: string): string {
		if (languageStore.value === 'zh') {
			return convertChinese(text, chineseScriptStore.value);
		}
		return text;
	}

	// Render text with Korean/Turkish optional characters styled (semi-transparent)
	// Patterns: (X)Y -> X is optional, shown faded | X/Y -> both are alternatives
	function renderTileHtml(text: string): string {
		// For Korean and Turkish, handle allomorph patterns
		if (languageStore.value !== 'ko' && languageStore.value !== 'tr') {
			// For other languages, just escape and return
			return escapeHtml(displayText(text));
		}

		// Use language-specific CSS class prefix
		const prefix = languageStore.value === 'ko' ? 'ko' : 'tr';

		// Check for slash pattern (e.g., "이/가", "았/었", "ler/lar", "de/da")
		if (text.includes('/')) {
			const parts = text.split('/');
			if (parts.length === 2) {
				return `<span class="${prefix}-alt">${escapeHtml(parts[0])}</span><span class="${prefix}-slash">/</span><span class="${prefix}-alt">${escapeHtml(parts[1])}</span>`;
			}
		}

		// Check for parentheses pattern (e.g., "(으)면", "(이)에요", "(y)e/a", "(n)in/ın")
		if (text.includes('(') && text.includes(')')) {
			// Parse the pattern: optional part in parens, rest is required
			const match = text.match(/^\(([^)]+)\)(.+)$/);
			if (match) {
				const optional = match[1];
				const required = match[2];
				// Check if rest also contains a slash (e.g., "(y)e/a")
				if (required.includes('/')) {
					const reqParts = required.split('/');
					if (reqParts.length === 2) {
						return `<span class="${prefix}-optional">${escapeHtml(optional)}</span><span class="${prefix}-alt">${escapeHtml(reqParts[0])}</span><span class="${prefix}-slash">/</span><span class="${prefix}-alt">${escapeHtml(reqParts[1])}</span>`;
					}
				}
				return `<span class="${prefix}-optional">${escapeHtml(optional)}</span>${escapeHtml(required)}`;
			}
		}

		return escapeHtml(text);
	}

	// Simple HTML escape for safety
	function escapeHtml(text: string): string {
		return text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#039;');
	}

	// Convert API tiles to internal TileData with stable IDs
	function apiTilesToTileData(apiTiles: ApiTile[]): TileData[] {
		return apiTiles.map((t, index) => ({
			id: `tile-${t.id}`,
			text: t.text,
			originalIndex: index
		}));
	}

	async function loadExercise() {
		loading = true;
		result = null;
		answerTiles = [];
		// Reset all saved language states for new exercise
		languageStates = { ja: null, zh: null, ko: null, tr: null };
		try {
			unifiedExercise = await fetchUnifiedExercise();
			// Initialize tiles for current language
			const langExercise = unifiedExercise.exercises[languageStore.value];
			if (langExercise) {
				bankTiles = apiTilesToTileData(langExercise.tiles);
			} else {
				// Fallback to first available language
				const firstLang = Object.keys(unifiedExercise.exercises)[0] as Language;
				if (firstLang) {
					languageStore.set(firstLang);
					bankTiles = apiTilesToTileData(unifiedExercise.exercises[firstLang]!.tiles);
				}
			}
		} catch (e) {
			console.error('Failed to load exercise:', e);
		} finally {
			loading = false;
		}
	}

	// Save current language state
	function saveCurrentLanguageState() {
		const currentLang = languageStore.value;
		languageStates[currentLang] = {
			answerTiles: [...answerTiles],
			bankTiles: [...bankTiles]
		};
	}

	// Switch language client-side (no API call!)
	function switchToLanguage(lang: Language) {
		if (!unifiedExercise || !unifiedExercise.exercises[lang]) return;

		// Save current state before switching
		saveCurrentLanguageState();

		languageStore.set(lang);
		result = null;

		// Check if we have saved state for this language
		const savedState = languageStates[lang];
		if (savedState) {
			// Restore saved state
			answerTiles = [...savedState.answerTiles];
			bankTiles = [...savedState.bankTiles];
		} else {
			// Initialize fresh tiles for new language
			answerTiles = [];
			bankTiles = apiTilesToTileData(unifiedExercise.exercises[lang]!.tiles);
		}
	}

	// Handle drag events for the answer zone
	function handleAnswerConsider(e: CustomEvent<{ items: TileData[] }>) {
		answerTiles = e.detail.items;
	}

	function handleAnswerFinalize(e: CustomEvent<{ items: TileData[] }>) {
		answerTiles = e.detail.items;
	}

	// Handle drag events for the bank zone
	function handleBankConsider(e: CustomEvent<{ items: TileData[] }>) {
		bankTiles = e.detail.items;
	}

	function handleBankFinalize(e: CustomEvent<{ items: TileData[] }>) {
		bankTiles = e.detail.items;
	}

	// Click-to-move: bank → answer (append to end)
	function selectTile(tile: TileData) {
		answerTiles = [...answerTiles, tile];
		bankTiles = bankTiles.filter((t) => t.id !== tile.id);
	}

	// Click-to-move: answer → bank (return to bank)
	function deselectTile(tile: TileData) {
		bankTiles = [...bankTiles, tile];
		answerTiles = answerTiles.filter((t) => t.id !== tile.id);
	}

	// Reset: return all tiles to bank and clear saved state
	function resetTiles() {
		if (currentExercise) {
			bankTiles = apiTilesToTileData(currentExercise.tiles);
			answerTiles = [];
			// Also clear saved state for current language
			languageStates[languageStore.value] = null;
		}
	}

	function submit() {
		if (!currentExercise || answerTiles.length === 0) return;
		const userTokens = answerTiles.map((t) => t.text);
		// Client-side grading with Korean-aware token comparison
		result = gradeUnifiedAnswer(currentExercise, userTokens, languageStore.value);
	}

	// Copy debug context to clipboard for pasting into an LLM
	let debugCopied = $state(false);
	async function copyDebugContext() {
		if (!unifiedExercise || !currentExercise) return;

		const langCode = languageStore.value;
		const langNames: Record<string, string> = { ja: 'Japanese', zh: 'Chinese', ko: 'Korean', tr: 'Turkish' };

		const context = `## Debug Context for duojp Exercise

**English:** ${unifiedExercise.english}
**Language:** ${langNames[langCode]} (${langCode})
**Target text:** ${currentExercise.text}
**Expected tokens:** ${JSON.stringify(currentExercise.tokens)}

**Current answer tiles:** ${JSON.stringify(answerTiles.map(t => t.text))}
**Bank tiles:** ${JSON.stringify(bankTiles.map(t => t.text))}
**All tiles:** ${JSON.stringify(currentExercise.tiles.map(t => t.text))}

${result ? `**Last result:** ${result.correct ? 'Correct' : 'Incorrect'}
**Expected:** ${result.expected}` : ''}

**Exercise ID:** ${unifiedExercise.exercise_id}
`;

		try {
			await navigator.clipboard.writeText(context);
			debugCopied = true;
			setTimeout(() => { debugCopied = false; }, 2000);
		} catch (err) {
			console.error('Failed to copy:', err);
		}
	}

	// Set class on document for Traditional Chinese font selection
	$effect(() => {
		if (typeof document !== 'undefined') {
			document.documentElement.classList.toggle('zh-traditional', chineseScriptStore.value === 'traditional');
		}
	});

	onMount(loadExercise);
</script>

<main>
	{#if loading}
		<div class="loading">Loading...</div>
	{:else if unifiedExercise && currentExercise}
		<section class="prompt">
			<p class="label">Translate this sentence:</p>
			<p class="english">{unifiedExercise.english}</p>
		</section>

		<!-- Language switcher - client-side, no reload! -->
		{#if availableLanguages.length > 0}
			<nav class="language-switcher">
				{#each availableLanguages as lang}
					<button
						class="lang-btn"
						class:active={lang.code === 'zh'
							? (languageStore.value === 'zh' && chineseScriptStore.value === 'simplified')
							: languageStore.value === lang.code}
						onclick={() => {
							switchToLanguage(lang.code);
							// When clicking China flag, set to simplified
							if (lang.code === 'zh') {
								chineseScriptStore.set('simplified');
							}
						}}
						title={lang.code === 'zh' ? 'Simplified Chinese' : lang.name}
					>
						{lang.flag}
					</button>
					<!-- Taiwan flag right after China flag -->
					{#if lang.code === 'zh'}
						<button
							class="lang-btn"
							class:active={languageStore.value === 'zh' && chineseScriptStore.value === 'traditional'}
							onclick={() => {
								if (languageStore.value !== 'zh') {
									switchToLanguage('zh');
								}
								chineseScriptStore.set('traditional');
							}}
							title="Traditional Chinese"
						>
							🇹🇼
						</button>
					{/if}
				{/each}
			</nav>
		{/if}

		<!-- Answer Area: Drop zone for building the sentence -->
		<section class="answer-area" data-lang={languageStore.value}>
			<div
				class="answer-box"
				use:dndzone={{
					items: answerTiles,
					flipDurationMs: FLIP_DURATION_MS,
					dropTargetStyle: { outline: 'rgba(88, 204, 2, 0.5) solid 2px' }
				}}
				onconsider={handleAnswerConsider}
				onfinalize={handleAnswerFinalize}
			>
				{#each answerTiles as tile (tile.id)}
					<button
						class="tile selected"
						animate:flip={{ duration: FLIP_DURATION_MS }}
						onclick={() => deselectTile(tile)}
						aria-label={displayText(tile.text)}
					>
						{@html renderTileHtml(tile.text)}
					</button>
				{/each}
				{#if answerTiles.length === 0}
					<span class="placeholder">Drag tiles here or click to add</span>
				{/if}
			</div>
		</section>

		<!-- Word Bank: Source tiles to pick from -->
		<section class="tile-bank-container" data-lang={languageStore.value}>
			<div
				class="tile-bank"
				use:dndzone={{
					items: bankTiles,
					flipDurationMs: FLIP_DURATION_MS,
					dropTargetStyle: { outline: 'rgba(28, 176, 246, 0.5) solid 2px' }
				}}
				onconsider={handleBankConsider}
				onfinalize={handleBankFinalize}
			>
				{#each bankTiles as tile (tile.id)}
					<button
						class="tile"
						animate:flip={{ duration: FLIP_DURATION_MS }}
						onclick={() => selectTile(tile)}
						aria-label={displayText(tile.text)}
					>
						{@html renderTileHtml(tile.text)}
					</button>
				{/each}
			</div>
		</section>

		<section class="actions">
			<button class="btn secondary" onclick={resetTiles} disabled={answerTiles.length === 0}>
				Reset
			</button>
			<button class="btn primary" onclick={submit} disabled={answerTiles.length === 0}>
				Check
			</button>
		</section>

		{#if result}
			<section class="result" class:correct={result.correct} class:incorrect={!result.correct} transition:fly={{ y: 20 }}>
				{#if result.correct}
					<div class="result-icon">✓</div>
					<p class="result-text">Correct! 🎉</p>
				{:else}
					<div class="result-icon">✗</div>
					<p class="result-text">Not quite right</p>
					<p class="expected">Expected: {displayText(result.expected)}</p>
				{/if}
				<button class="btn next" onclick={loadExercise}>Next Exercise →</button>
			</section>
		{/if}

		<!-- Debug button to copy context for LLM -->
		<button class="debug-copy-btn" onclick={copyDebugContext} title="Copy debug context for LLM">
			{debugCopied ? '✓ Copied!' : '📋 Copy Context'}
		</button>
	{/if}
</main>

<style>
	main {
		width: 100%;
		max-width: 600px;
		margin: 0 auto;
		padding: 1rem;
		box-sizing: border-box;
	}

	.language-switcher {
		display: flex;
		justify-content: center;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.lang-btn {
		padding: 0.4rem 0.6rem;
		border: 2px solid var(--border-color);
		border-radius: 8px;
		background: var(--bg-secondary);
		font-size: 1.2rem;
		cursor: pointer;
		transition: all 0.15s ease;
		opacity: 0.6;
	}

	.lang-btn:hover {
		opacity: 1;
		transform: scale(1.1);
	}

	.lang-btn.active {
		opacity: 1;
		border-color: var(--green-primary);
		background: var(--bg-tertiary);
	}

	.loading {
		text-align: center;
		color: var(--text-secondary);
		font-size: 1.2rem;
		padding: 2rem;
	}

	.prompt {
		background: var(--bg-secondary);
		padding: 1.5rem;
		border-radius: 16px;
		margin-bottom: 1.5rem;
		box-shadow: 0 2px 8px var(--shadow-color);
	}

	.label {
		color: var(--text-secondary);
		margin: 0 0 0.5rem;
		font-size: 0.9rem;
	}

	.english {
		font-size: 1.4rem;
		color: var(--text-primary);
		margin: 0;
		font-weight: 500;
	}

	/* Answer area - where user builds the sentence */
	.answer-area {
		margin-bottom: 1.5rem;
	}

	.answer-box {
		min-height: 70px;
		background: var(--bg-secondary);
		border: 2px dashed var(--border-dashed);
		border-radius: 16px;
		padding: 0.75rem;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		align-content: flex-start;
		gap: 0.25rem;
		transition: border-color 0.2s, background-color 0.2s;
	}

	.answer-box:empty::before,
	.placeholder {
		color: var(--text-muted);
		font-style: italic;
		padding: 0.5rem;
	}

	/* Word bank - source tiles */
	.tile-bank-container {
		background: var(--bg-tertiary);
		border-radius: 16px;
		padding: 0.75rem;
		margin-bottom: 1rem;
	}

	.tile-bank {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		min-height: 60px;
		gap: 0.25rem;
		align-content: flex-start;
	}

	/* Tile styling - base */
	.tile {
		padding: 0.6rem 1rem;
		border: 2px solid var(--tile-border);
		border-radius: 12px;
		background: var(--tile-bg);
		color: var(--text-primary);
		font-size: 1.1rem;
		line-height: 1.4;
		min-height: 1.4em;
		cursor: grab;
		transition: all 0.15s ease;
		box-shadow: 0 2px 0 var(--tile-shadow);
		font-family: 'Geist', sans-serif;
		user-select: none;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	/* Language-specific fonts for tiles */
	[data-lang='ja'] .tile {
		font-family: 'Zen Kaku Gothic New', 'Noto Sans JP', sans-serif;
	}

	[data-lang='zh'] .tile {
		font-family: 'Noto Sans SC', 'PingFang SC', sans-serif;
	}

	/* Traditional Chinese - check if user has Taiwan script selected */
	:global(.zh-traditional) [data-lang='zh'] .tile {
		font-family: 'Noto Sans TC', 'PingFang TC', sans-serif;
	}

	[data-lang='ko'] .tile {
		font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif;
	}

	[data-lang='tr'] .tile {
		font-family: 'Geist', sans-serif;
	}

	.tile:hover {
		background: var(--bg-tertiary);
		transform: translateY(-1px);
	}

	.tile:active {
		cursor: grabbing;
		transform: translateY(2px);
		box-shadow: none;
	}

	.tile.selected {
		background: var(--blue-primary);
		color: white;
		border-color: var(--blue-dark);
		box-shadow: 0 2px 0 var(--blue-dark);
	}

	.tile.selected:hover {
		filter: brightness(1.1);
	}

	/* Korean allomorph styling - optional/alternative characters */
	.tile :global(.ko-optional) {
		opacity: 0.45;
	}

	.tile :global(.ko-alt) {
		opacity: 0.85;
	}

	.tile :global(.ko-slash) {
		opacity: 0.4;
		font-size: 0.85em;
		margin: 0 0.05em;
	}

	/* Adjust opacity for selected tiles (on blue background) */
	.tile.selected :global(.ko-optional) {
		opacity: 0.5;
	}

	.tile.selected :global(.ko-alt) {
		opacity: 0.9;
	}

	.tile.selected :global(.ko-slash) {
		opacity: 0.5;
	}

	/* Turkish allomorph styling - vowel harmony variants */
	.tile :global(.tr-optional) {
		opacity: 0.45;
	}

	.tile :global(.tr-alt) {
		opacity: 0.85;
	}

	.tile :global(.tr-slash) {
		opacity: 0.4;
		font-size: 0.85em;
		margin: 0 0.05em;
	}

	/* Adjust opacity for selected tiles (on blue background) */
	.tile.selected :global(.tr-optional) {
		opacity: 0.5;
	}

	.tile.selected :global(.tr-alt) {
		opacity: 0.9;
	}

	.tile.selected :global(.tr-slash) {
		opacity: 0.5;
	}

	/* Actions */
	.actions {
		display: flex;
		gap: 1rem;
		justify-content: center;
		margin-top: 1.5rem;
	}

	.btn {
		padding: 0.75rem 2rem;
		border: none;
		border-radius: 12px;
		font-size: 1rem;
		font-weight: 600;
		font-family: 'Geist', sans-serif;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn.primary {
		background: var(--green-primary);
		color: white;
		box-shadow: 0 4px 0 var(--green-dark);
	}

	.btn.primary:hover:not(:disabled) {
		filter: brightness(1.1);
	}

	.btn.primary:active:not(:disabled) {
		transform: translateY(4px);
		box-shadow: none;
	}

	.btn.secondary {
		background: var(--bg-secondary);
		color: var(--text-secondary);
		border: 2px solid var(--border-color);
	}

	.btn.secondary:hover:not(:disabled) {
		background: var(--bg-tertiary);
	}

	/* Result panel */
	.result {
		margin-top: 1.5rem;
		padding: 1.5rem;
		border-radius: 16px;
		text-align: center;
	}

	.result.correct {
		background: #d7ffb8;
		border: 2px solid var(--green-primary);
	}

	:global(.dark) .result.correct {
		background: rgba(74, 222, 128, 0.2);
	}

	.result.incorrect {
		background: #ffdfe0;
		border: 2px solid #ff4b4b;
	}

	:global(.dark) .result.incorrect {
		background: rgba(248, 113, 113, 0.2);
	}

	.result-icon {
		font-size: 2rem;
		margin-bottom: 0.5rem;
	}

	.result.correct .result-icon {
		color: var(--green-primary);
	}

	.result.incorrect .result-icon {
		color: #ff4b4b;
	}

	.result-text {
		font-size: 1.2rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
		color: var(--text-primary);
	}

	.expected {
		color: var(--text-secondary);
		margin: 0.5rem 0 1rem;
		font-size: 1.1rem;
	}

	.btn.next {
		background: var(--blue-primary);
		color: white;
		box-shadow: 0 4px 0 var(--blue-dark);
	}

	.btn.next:hover {
		filter: brightness(1.1);
	}

	/* Debug copy button - small, unobtrusive at bottom */
	.debug-copy-btn {
		position: fixed;
		bottom: 1rem;
		right: 1rem;
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
		background: var(--bg-tertiary);
		color: var(--text-muted);
		border: 1px solid var(--border-color);
		border-radius: 6px;
		cursor: pointer;
		opacity: 0.6;
		transition: opacity 0.2s, background 0.2s;
	}

	.debug-copy-btn:hover {
		opacity: 1;
		background: var(--bg-secondary);
		color: var(--text-primary);
	}
</style>
