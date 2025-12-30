import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Supported languages and their data paths
type Language = 'ja' | 'zh';
const LANGUAGE_DATA_PATHS: Record<Language, string> = {
	ja: '/data',      // Japanese - default
	zh: '/data-zh'    // Chinese (Mandarin)
};

interface Manifest {
	total: number;
	chunks: number;
	chunk_size: number;
	source: string;
	language?: string;
}

interface SentenceJa {
	id: number;
	en: string;
	ja: string;
	tokens: string[];
}

interface SentenceZh {
	id: number;
	en: string;
	zh: string;
	tokens: string[];
}

type Sentence = SentenceJa | SentenceZh;

interface TileData {
	id: number;
	text: string;
}

// Cache manifest and distractors per language
const cachedManifests: Partial<Record<Language, Manifest>> = {};
const cachedDistractors: Partial<Record<Language, string[]>> = {};

async function fetchJSON<T>(fetch: typeof globalThis.fetch, url: string): Promise<T> {
	const response = await fetch(url);
	if (!response.ok) {
		throw new Error(`Failed to fetch ${url}: ${response.status}`);
	}
	return response.json();
}

function getDataPath(lang: Language): string {
	return LANGUAGE_DATA_PATHS[lang] || LANGUAGE_DATA_PATHS.ja;
}

async function getManifest(fetch: typeof globalThis.fetch, lang: Language): Promise<Manifest> {
	if (!cachedManifests[lang]) {
		const dataPath = getDataPath(lang);
		cachedManifests[lang] = await fetchJSON<Manifest>(fetch, `${dataPath}/manifest.json`);
	}
	return cachedManifests[lang]!;
}

async function getDistractors(fetch: typeof globalThis.fetch, lang: Language): Promise<string[]> {
	if (!cachedDistractors[lang]) {
		const dataPath = getDataPath(lang);
		cachedDistractors[lang] = await fetchJSON<string[]>(fetch, `${dataPath}/distractors.json`);
	}
	return cachedDistractors[lang]!;
}

function shuffle<T>(array: T[]): T[] {
	const result = [...array];
	for (let i = result.length - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1));
		[result[i], result[j]] = [result[j], result[i]];
	}
	return result;
}

function getTargetText(sentence: Sentence, lang: Language): string {
	if (lang === 'zh') {
		return (sentence as SentenceZh).zh;
	}
	return (sentence as SentenceJa).ja;
}

export const GET: RequestHandler = async ({ fetch, url }) => {
	try {
		// Get language from query param (default: Japanese)
		const langParam = url.searchParams.get('lang');
		const lang: Language = (langParam === 'zh') ? 'zh' : 'ja';
		const dataPath = getDataPath(lang);

		// Load manifest to know total sentences
		const manifest = await getManifest(fetch, lang);
		const distractors = await getDistractors(fetch, lang);

		// Pick a random sentence
		const sentenceIndex = Math.floor(Math.random() * manifest.total);
		const chunkIndex = Math.floor(sentenceIndex / manifest.chunk_size);
		const indexInChunk = sentenceIndex % manifest.chunk_size;

		// Fetch the chunk
		const chunk = await fetchJSON<Sentence[]>(
			fetch,
			`${dataPath}/chunks/${chunkIndex}.json`
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

		const targetText = getTargetText(sentence, lang);

		return json({
			exercise_id: sentence.id,
			english: sentence.en,
			tiles,
			expected: targetText,
			num_correct_tiles: correctTokens.length,
			language: lang
		});
	} catch (error) {
		console.error('Error generating exercise:', error);
		return json({ error: 'Failed to generate exercise' }, { status: 500 });
	}
};

