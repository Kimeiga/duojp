import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Configuration - can switch to jsDelivr for production
const DATA_BASE_URL = '/data'; // Local static files
// const DATA_BASE_URL = 'https://cdn.jsdelivr.net/gh/username/duojp-data@main';

interface Manifest {
	total: number;
	chunks: number;
	chunk_size: number;
	source: string;
}

interface Sentence {
	id: number;
	en: string;
	ja: string;
	tokens: string[];
}

interface TileData {
	id: number;
	text: string;
}

// Cache manifest and distractors in memory
let cachedManifest: Manifest | null = null;
let cachedDistractors: string[] | null = null;

async function fetchJSON<T>(fetch: typeof globalThis.fetch, url: string): Promise<T> {
	const response = await fetch(url);
	if (!response.ok) {
		throw new Error(`Failed to fetch ${url}: ${response.status}`);
	}
	return response.json();
}

async function getManifest(fetch: typeof globalThis.fetch): Promise<Manifest> {
	if (!cachedManifest) {
		cachedManifest = await fetchJSON<Manifest>(fetch, `${DATA_BASE_URL}/manifest.json`);
	}
	return cachedManifest;
}

async function getDistractors(fetch: typeof globalThis.fetch): Promise<string[]> {
	if (!cachedDistractors) {
		cachedDistractors = await fetchJSON<string[]>(fetch, `${DATA_BASE_URL}/distractors.json`);
	}
	return cachedDistractors;
}

function shuffle<T>(array: T[]): T[] {
	const result = [...array];
	for (let i = result.length - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1));
		[result[i], result[j]] = [result[j], result[i]];
	}
	return result;
}

export const GET: RequestHandler = async ({ fetch }) => {
	try {
		// Load manifest to know total sentences
		const manifest = await getManifest(fetch);
		const distractors = await getDistractors(fetch);

		// Pick a random sentence
		const sentenceIndex = Math.floor(Math.random() * manifest.total);
		const chunkIndex = Math.floor(sentenceIndex / manifest.chunk_size);
		const indexInChunk = sentenceIndex % manifest.chunk_size;

		// Fetch the chunk
		const chunk = await fetchJSON<Sentence[]>(
			fetch,
			`${DATA_BASE_URL}/chunks/${chunkIndex}.json`
		);

		const sentence = chunk[indexInChunk];
		if (!sentence) {
			return json({ error: 'Sentence not found' }, { status: 404 });
		}

		// Build tiles: correct tokens + distractors
		const correctTokens = sentence.tokens;
		const numDistractors = Math.min(
			Math.max(3, Math.floor(correctTokens.length * 0.5)),
			8
		);

		// Pick distractors that aren't in the correct answer
		const correctSet = new Set(correctTokens);
		const availableDistractors = distractors.filter((d) => !correctSet.has(d));
		const selectedDistractors = shuffle(availableDistractors).slice(0, numDistractors);

		// Combine and shuffle all tiles
		const allTokens = [...correctTokens, ...selectedDistractors];
		const shuffledTokens = shuffle(allTokens);

		const tiles: TileData[] = shuffledTokens.map((text, index) => ({
			id: index,
			text
		}));

		return json({
			exercise_id: sentence.id,
			english: sentence.en,
			tiles,
			expected: sentence.ja, // For grading
			num_correct_tiles: correctTokens.length
		});
	} catch (error) {
		console.error('Error generating exercise:', error);
		return json({ error: 'Failed to generate exercise' }, { status: 500 });
	}
};

