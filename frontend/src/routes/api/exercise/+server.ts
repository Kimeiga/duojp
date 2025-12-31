import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Supported languages
type Language = 'ja' | 'zh' | 'ko' | 'tr';

// Unified data format - all translations in one object
interface UnifiedManifest {
	total: number;
	chunks: number;
	chunk_size: number;
	languages: Language[];
}

interface TranslationData {
	text: string;
	tokens: string[];
}

interface UnifiedSentence {
	id: number;
	en: string;
	translations: {
		ja?: TranslationData;
		zh?: TranslationData;
		ko?: TranslationData;
		tr?: TranslationData;
	};
}

interface TileData {
	id: number;
	text: string;
}

interface LanguageExercise {
	text: string;
	tokens: string[];
	tiles: TileData[];
	num_correct_tiles: number;
}

// Cache
let cachedManifest: UnifiedManifest | null = null;
let cachedDistractors: Record<Language, string[]> | null = null;

const DATA_PATH = '/data-unified';

async function fetchJSON<T>(fetch: typeof globalThis.fetch, url: string): Promise<T> {
	const response = await fetch(url);
	if (!response.ok) {
		throw new Error(`Failed to fetch ${url}: ${response.status}`);
	}
	return response.json();
}

async function getManifest(fetch: typeof globalThis.fetch): Promise<UnifiedManifest> {
	if (!cachedManifest) {
		cachedManifest = await fetchJSON<UnifiedManifest>(fetch, `${DATA_PATH}/manifest.json`);
	}
	return cachedManifest;
}

async function getDistractors(fetch: typeof globalThis.fetch): Promise<Record<Language, string[]>> {
	if (!cachedDistractors) {
		cachedDistractors = await fetchJSON<Record<Language, string[]>>(fetch, `${DATA_PATH}/distractors.json`);
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

// Punctuation characters to filter from tokens (safety net for any edge cases in pre-tokenized data)
const PUNCTUATION_CHARS = new Set([
	// CJK punctuation
	'。', '，', '、', '；', '：', '？', '！', '…', '—', '·',
	'「', '」', '『', '』', '（', '）', '【', '】', '《', '》', '〈', '〉',
	// Curly quotes (using Unicode escapes to avoid syntax issues)
	'\u201C', '\u201D', '\u2018', '\u2019', // " " ' '
	// General punctuation
	'.', ',', ';', ':', '?', '!', '(', ')', '[', ']',
	'"', "'", '-', '–', '—', ' ', '\t', '\n',
	// Additional edge cases
	'～', '〜', '．', '＇', '＂'
]);

/**
 * Check if a token is valid for display as a tile.
 * Filters out tokens that are purely punctuation or have other issues.
 */
function isValidToken(token: string): boolean {
	// Must have some content
	if (!token || token.trim().length === 0) return false;

	// Check if purely punctuation
	const isPurelyPunctuation = [...token].every((c) => PUNCTUATION_CHARS.has(c));
	if (isPurelyPunctuation) return false;

	// Check if token starts or ends with quotation marks (malformed tokenization)
	// Using Unicode escapes for curly quotes: \u201C " \u201D " \u2018 ' \u2019 '
	if (/^["\u201C\u201D'\u2018\u2019]/.test(token) || /["\u201C\u201D'\u2018\u2019]$/.test(token))
		return false;

	return true;
}

function buildExerciseForLanguage(
	translation: TranslationData,
	distractors: string[]
): LanguageExercise {
	// Filter out any invalid tokens (punctuation, malformed tokens)
	const correctTokens = translation.tokens.filter(isValidToken);

	const numDistractors = Math.min(
		Math.max(3, Math.floor(correctTokens.length * 0.5)),
		8
	);

	// Pick distractors that aren't in the correct answer and are valid
	const correctSet = new Set(correctTokens);
	const availableDistractors = distractors.filter(
		(d) => !correctSet.has(d) && isValidToken(d)
	);
	const selectedDistractors = shuffle(availableDistractors).slice(0, numDistractors);

	// Combine and shuffle all tiles
	const allTokens = [...correctTokens, ...selectedDistractors];
	const shuffledTokens = shuffle(allTokens);

	const tiles: TileData[] = shuffledTokens.map((text, index) => ({
		id: index,
		text
	}));

	return {
		text: translation.text,
		tokens: correctTokens,
		tiles,
		num_correct_tiles: correctTokens.length
	};
}

// Pattern to detect multi-dialogue sentences (e.g. "Hello." "Hi there.")
// These have a closing curly quote, space, and opening curly quote
const MULTI_DIALOGUE_PATTERN = /"\s+"/;

// Check if a sentence is suitable for an exercise
function isSuitableSentence(sentence: UnifiedSentence): boolean {
	// Skip multi-dialogue sentences (multiple quoted exchanges in one)
	if (MULTI_DIALOGUE_PATTERN.test(sentence.en)) {
		return false;
	}
	return true;
}

export const GET: RequestHandler = async ({ fetch }) => {
	try {
		// Load manifest and distractors
		const manifest = await getManifest(fetch);
		const allDistractors = await getDistractors(fetch);

		// Try to find a suitable sentence (with retry logic)
		const MAX_ATTEMPTS = 10;
		let sentence: UnifiedSentence | null = null;

		for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
			// Pick a random sentence
			const sentenceIndex = Math.floor(Math.random() * manifest.total);
			const chunkIndex = Math.floor(sentenceIndex / manifest.chunk_size);
			const indexInChunk = sentenceIndex % manifest.chunk_size;

			// Fetch the chunk
			const chunk = await fetchJSON<UnifiedSentence[]>(
				fetch,
				`${DATA_PATH}/chunks/${chunkIndex}.json`
			);

			const candidate = chunk[indexInChunk];
			if (candidate && isSuitableSentence(candidate)) {
				sentence = candidate;
				break;
			}
		}

		if (!sentence) {
			return json({ error: 'Could not find suitable sentence' }, { status: 404 });
		}

		// Build exercises for all available languages
		const exercises: Partial<Record<Language, LanguageExercise>> = {};

		for (const lang of ['ja', 'zh', 'ko', 'tr'] as Language[]) {
			const translation = sentence.translations[lang];
			const distractors = allDistractors[lang] || [];

			if (translation && translation.tokens && translation.tokens.length > 0) {
				exercises[lang] = buildExerciseForLanguage(translation, distractors);
			}
		}

		// Return unified response with all translations
		return json({
			exercise_id: sentence.id,
			english: sentence.en,
			exercises  // Contains ja, zh, ko with tiles for each
		});
	} catch (error) {
		console.error('Error generating exercise:', error);
		return json({ error: 'Failed to generate exercise' }, { status: 500 });
	}
};

