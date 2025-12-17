import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Configuration
const DATA_BASE_URL = '/data';

interface Sentence {
	id: number;
	en: string;
	ja: string;
	tokens: string[];
}

// Punctuation to strip for grading
const PUNCTUATION_CHARS = new Set([
	'。', '、', '．', '，', '.', ',', '！', '？', '!', '?', '…', '・',
	'「', '」', '『', '』', '（', '）', '(', ')', '【', '】', '〈', '〉', '《', '》'
]);

function normalizeForGrading(text: string): string {
	// NFKC normalization (JavaScript's normalize)
	let normalized = text.normalize('NFKC');
	// Remove whitespace
	normalized = normalized.replace(/\s+/g, '');
	// Remove punctuation
	normalized = [...normalized].filter((c) => !PUNCTUATION_CHARS.has(c)).join('');
	return normalized;
}

export const POST: RequestHandler = async ({ request, fetch }) => {
	try {
		const body = await request.json();
		const { exercise_id, answer } = body;

		if (typeof exercise_id !== 'number' || typeof answer !== 'string') {
			return json({ error: 'Invalid request body' }, { status: 400 });
		}

		// Find the sentence in its chunk
		const chunkIndex = Math.floor(exercise_id / 1000);
		const indexInChunk = exercise_id % 1000;

		const response = await fetch(`${DATA_BASE_URL}/chunks/${chunkIndex}.json`);
		if (!response.ok) {
			return json({ error: 'Chunk not found' }, { status: 404 });
		}

		const chunk: Sentence[] = await response.json();
		const sentence = chunk.find((s) => s.id === exercise_id);

		if (!sentence) {
			return json({ error: 'Sentence not found' }, { status: 404 });
		}

		// Normalize and compare
		const normalizedAnswer = normalizeForGrading(answer);
		const normalizedExpected = normalizeForGrading(sentence.ja);

		const correct = normalizedAnswer === normalizedExpected;

		return json({
			correct,
			submitted: answer,
			expected: sentence.ja
		});
	} catch (error) {
		console.error('Error grading:', error);
		return json({ error: 'Failed to grade' }, { status: 500 });
	}
};

