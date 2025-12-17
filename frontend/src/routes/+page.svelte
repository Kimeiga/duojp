<script lang="ts">
	import { onMount } from 'svelte';
	import { fly } from 'svelte/transition';
	import { flip } from 'svelte/animate';
	import { dndzone } from 'svelte-dnd-action';
	import { fetchExercise, gradeAnswer } from '$lib/api';
	import type { Exercise, TileData, GradeResult, ApiTile } from '$lib/types';

	// Animation duration for flip transitions
	const FLIP_DURATION_MS = 200;

	let exercise: Exercise | null = $state(null);
	let answerTiles: TileData[] = $state([]);
	let bankTiles: TileData[] = $state([]);
	let result: GradeResult | null = $state(null);
	let loading = $state(true);
	let submitting = $state(false);

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
			exercise = await fetchExercise();
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

	async function submit() {
		if (!exercise || answerTiles.length === 0) return;
		submitting = true;
		const answer = answerTiles.map((t) => t.text).join('');
		try {
			result = await gradeAnswer(exercise.exercise_id, answer);
		} catch (e) {
			console.error('Failed to grade:', e);
		} finally {
			submitting = false;
		}
	}

	onMount(loadExercise);
</script>

<main>
	<header>
		<h1>🇯🇵 Japanese Sentence Builder</h1>
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
						aria-label={tile.text}
					>
						{tile.text}
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
						aria-label={tile.text}
					>
						{tile.text}
					</button>
				{/each}
			</div>
		</section>

		<section class="actions">
			<button class="btn secondary" onclick={resetTiles} disabled={answerTiles.length === 0}>
				Reset
			</button>
			<button class="btn primary" onclick={submit} disabled={answerTiles.length === 0 || submitting}>
				{submitting ? 'Checking...' : 'Check'}
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
					<p class="expected">Expected: {result.expected}</p>
				{/if}
				<button class="btn next" onclick={loadExercise}>Next Exercise →</button>
			</section>
		{/if}
	{/if}
</main>

<style>
	:global(body) {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		background: #f0f0f0;
	}

	main {
		max-width: 600px;
		margin: 0 auto;
		padding: 1rem;
		min-height: 100vh;
	}

	header h1 {
		text-align: center;
		color: #58cc02;
		font-size: 1.5rem;
		margin-bottom: 2rem;
	}

	.loading {
		text-align: center;
		color: #777;
		font-size: 1.2rem;
		padding: 2rem;
	}

	.prompt {
		background: white;
		padding: 1.5rem;
		border-radius: 16px;
		margin-bottom: 1.5rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
	}

	.label {
		color: #777;
		margin: 0 0 0.5rem;
		font-size: 0.9rem;
	}

	.english {
		font-size: 1.4rem;
		color: #333;
		margin: 0;
		font-weight: 500;
	}

	/* Answer area - where user builds the sentence */
	.answer-area {
		margin-bottom: 1.5rem;
	}

	.answer-box {
		min-height: 70px;
		background: white;
		border: 2px dashed #ccc;
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
		color: #aaa;
		font-style: italic;
		padding: 0.5rem;
	}

	/* Word bank - source tiles */
	.tile-bank-container {
		background: #e8e8e8;
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
		border: 2px solid #e5e5e5;
		border-radius: 12px;
		background: white;
		font-size: 1.1rem;
		cursor: grab;
		transition: all 0.15s ease;
		box-shadow: 0 2px 0 #e5e5e5;
		font-family: 'Hiragino Kaku Gothic Pro', 'Yu Gothic', 'Noto Sans JP', sans-serif;
		user-select: none;
	}

	.tile:hover {
		background: #f7f7f7;
		transform: translateY(-1px);
	}

	.tile:active {
		cursor: grabbing;
		transform: translateY(2px);
		box-shadow: none;
	}

	.tile.selected {
		background: #1cb0f6;
		color: white;
		border-color: #1899d6;
		box-shadow: 0 2px 0 #1899d6;
	}

	.tile.selected:hover {
		background: #1ec3ff;
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
		background: #58cc02;
		color: white;
		box-shadow: 0 4px 0 #46a302;
	}

	.btn.primary:hover:not(:disabled) {
		background: #61e002;
	}

	.btn.primary:active:not(:disabled) {
		transform: translateY(4px);
		box-shadow: none;
	}

	.btn.secondary {
		background: white;
		color: #777;
		border: 2px solid #e5e5e5;
	}

	.btn.secondary:hover:not(:disabled) {
		background: #f7f7f7;
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
		border: 2px solid #58cc02;
	}

	.result.incorrect {
		background: #ffdfe0;
		border: 2px solid #ff4b4b;
	}

	.result-icon {
		font-size: 2rem;
		margin-bottom: 0.5rem;
	}

	.result.correct .result-icon {
		color: #58cc02;
	}

	.result.incorrect .result-icon {
		color: #ff4b4b;
	}

	.result-text {
		font-size: 1.2rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
	}

	.expected {
		color: #666;
		margin: 0.5rem 0 1rem;
		font-size: 1.1rem;
	}

	.btn.next {
		background: #1cb0f6;
		color: white;
		box-shadow: 0 4px 0 #1899d6;
	}

	.btn.next:hover {
		background: #1ec3ff;
	}
</style>
