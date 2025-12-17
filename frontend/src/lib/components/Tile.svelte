<script lang="ts">
	import { scale } from 'svelte/transition';
	import { backOut } from 'svelte/easing';

	interface Props {
		text: string;
		selected?: boolean;
		disabled?: boolean;
		onclick?: () => void;
	}

	let { text, selected = false, disabled = false, onclick }: Props = $props();
</script>

<button
	class="tile"
	class:selected
	class:disabled
	{onclick}
	{disabled}
	transition:scale={{ duration: 200, easing: backOut }}
>
	{text}
</button>

<style>
	.tile {
		padding: 0.6rem 1rem;
		margin: 0.25rem;
		border: 2px solid #e5e5e5;
		border-radius: 12px;
		background: white;
		font-size: 1.1rem;
		cursor: pointer;
		transition: all 0.15s ease;
		box-shadow: 0 2px 0 #e5e5e5;
		font-family: 'Hiragino Kaku Gothic Pro', 'Yu Gothic', sans-serif;
	}

	.tile:hover:not(.disabled) {
		background: #f7f7f7;
		transform: translateY(-1px);
	}

	.tile:active:not(.disabled) {
		transform: translateY(2px);
		box-shadow: none;
	}

	.tile.selected {
		background: #1cb0f6;
		color: white;
		border-color: #1899d6;
		box-shadow: 0 2px 0 #1899d6;
	}

	.tile.disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
</style>

