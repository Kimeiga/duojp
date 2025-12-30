<script lang="ts">
	import { onMount } from 'svelte';
	import { fly } from 'svelte/transition';
	import { flip } from 'svelte/animate';
	import { dndzone } from 'svelte-dnd-action';
	import { fetchExercise, gradeAnswer } from '$lib/api';
	import { languageStore } from '$lib/stores/language.svelte';
	import { chineseScriptStore } from '$lib/stores/chineseScript.svelte';
	import { convertChinese } from '$lib/chineseConverter';
	import { LANGUAGES, type Exercise, type TileData, type GradeResult, type ApiTile } from '$lib/types';

	// Animation duration for flip transitions
	const FLIP_DURATION_MS = 200;

	let exercise: Exercise | null = $state(null);
	let answerTiles: TileData[] = $state([]);
	let bankTiles: TileData[] = $state([]);
	let result: GradeResult | null = $state(null);
	let loading = $state(true);

	// Get current language info for display
	const currentLangInfo = $derived(LANGUAGES.find((l) => l.code === languageStore.value) || LANGUAGES[0]);

	// Helper to convert text for Chinese display
	function displayText(text: string): string {
		if (languageStore.value === 'zh') {
			return convertChinese(text, chineseScriptStore.value);
		}
		return text;
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
		try {
			exercise = await fetchExercise(languageStore.value);
			bankTiles = apiTilesToTileData(exercise.tiles);
		} catch (e) {
			console.error('Failed to load exercise:', e);
		} finally {
			loading = false;
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

	// Reset: return all tiles to bank
	function resetTiles() {
		if (exercise) {
			bankTiles = apiTilesToTileData(exercise.tiles);
			answerTiles = [];
		}
	}

	function submit() {
		if (!exercise || answerTiles.length === 0) return;
		const answer = answerTiles.map((t) => t.text).join('');
		// Client-side grading - instant feedback, works offline
		result = gradeAnswer(exercise, answer);
	}

	onMount(loadExercise);
</script>

<main>
	<header>
		<h1>{currentLangInfo.nativeName} Sentence Builder</h1>
	</header>

	{#if loading}
		<div class="loading">Loading...</div>
	{:else if exercise}
		<section class="prompt">
			<p class="label">Translate this sentence:</p>
			<p class="english">{exercise.english}</p>
		</section>

		<!-- Answer Area: Drop zone for building the sentence -->
		<section class="answer-area">
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
						{displayText(tile.text)}
					</button>
				{/each}
				{#if answerTiles.length === 0}
					<span class="placeholder">Drag tiles here or click to add</span>
				{/if}
			</div>
		</section>

		<!-- Word Bank: Source tiles to pick from -->
		<section class="tile-bank-container">
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
						{displayText(tile.text)}
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

	header h1 {
		text-align: center;
		color: var(--green-primary);
		font-size: 1.5rem;
		margin-bottom: 2rem;
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

	/* Tile styling */
	.tile {
		padding: 0.6rem 1rem;
		border: 2px solid var(--tile-border);
		border-radius: 12px;
		background: var(--tile-bg);
		color: var(--text-primary);
		font-size: 1.1rem;
		cursor: grab;
		transition: all 0.15s ease;
		box-shadow: 0 2px 0 var(--tile-shadow);
		font-family: 'Hiragino Kaku Gothic Pro', 'Yu Gothic', 'Noto Sans JP', sans-serif;
		user-select: none;
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
</style>
