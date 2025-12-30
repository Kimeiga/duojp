import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Supported languages and their data paths
type Language = 'ja' | 'zh';
const LANGUAGE_DATA_PATHS: Record<Language, string> = {
	ja: '/data',
	zh: '/data-zh'
};

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

// Punctuation to strip for grading (Japanese + Chinese)
const PUNCTUATION_CHARS = new Set([
	// Japanese
	'。', '、', '．', '，', '.', ',', '！', '？', '!', '?', '…', '・',
	'「', '」', '『', '』', '（', '）', '(', ')', '【', '】', '〈', '〉', '《', '》',
	// Chinese-specific
	'；', '：', '\u201C', '\u201D', '\u2018', '\u2019', '—', '～'
]);

function normalizeForGrading(text: string): string {
	let normalized = text.normalize('NFKC');
	normalized = normalized.replace(/\s+/g, '');
	normalized = [...normalized].filter((c) => !PUNCTUATION_CHARS.has(c)).join('');
	return normalized;
}

function getTargetText(sentence: Sentence, lang: Language): string {
	if (lang === 'zh') {
		return (sentence as SentenceZh).zh;
	}
	return (sentence as SentenceJa).ja;
}

function getDataPath(lang: Language): string {
	return LANGUAGE_DATA_PATHS[lang] || LANGUAGE_DATA_PATHS.ja;
}

export const POST: RequestHandler = async ({ request, fetch }) => {
	try {
		const body = await request.json();
		const { exercise_id, answer, language } = body;

		if (typeof exercise_id !== 'number' || typeof answer !== 'string') {
			return json({ error: 'Invalid request body' }, { status: 400 });
		}

		const lang: Language = (language === 'zh') ? 'zh' : 'ja';
		const dataPath = getDataPath(lang);

		// Find the sentence in its chunk
		const chunkIndex = Math.floor(exercise_id / 1000);

		const response = await fetch(`${dataPath}/chunks/${chunkIndex}.json`);
		if (!response.ok) {
			return json({ error: 'Chunk not found' }, { status: 404 });
		}

		const chunk: Sentence[] = await response.json();
		const sentence = chunk.find((s) => s.id === exercise_id);

		if (!sentence) {
			return json({ error: 'Sentence not found' }, { status: 404 });
		}

		const expected = getTargetText(sentence, lang);

		// Normalize and compare
		const normalizedAnswer = normalizeForGrading(answer);
		const normalizedExpected = normalizeForGrading(expected);

		const correct = normalizedAnswer === normalizedExpected;

		return json({
			correct,
			submitted: answer,
			expected
		});
	} catch (error) {
		console.error('Error grading:', error);
		return json({ error: 'Failed to grade' }, { status: 500 });
	}
};

