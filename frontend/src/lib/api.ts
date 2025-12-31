import type { Exercise, GradeResult, Language, UnifiedExercise, LanguageExercise } from './types';

const API_BASE = '/api';

/**
 * Fetch a unified exercise with all language translations.
 */
export async function fetchUnifiedExercise(): Promise<UnifiedExercise> {
	const res = await fetch(`${API_BASE}/exercise`);
	if (!res.ok) throw new Error('Failed to fetch exercise');
	return res.json();
}

/**
 * Legacy: Fetch exercise for a single language.
 * @deprecated Use fetchUnifiedExercise instead
 */
export async function fetchExercise(language: Language = 'ja'): Promise<Exercise> {
	const res = await fetch(`${API_BASE}/exercise?lang=${language}`);
	if (!res.ok) throw new Error('Failed to fetch exercise');
	return res.json();
}

/**
 * Normalize text for comparison - removes whitespace and punctuation.
 */
function normalize(s: string): string {
	return s
		.replace(/\s+/g, '')  // Remove whitespace
		.replace(/[。，、；：？！…—·「」『』（）【】《》""''〈〉.,;:?!()\[\]"']/g, '')  // Remove CJK + Western punctuation
		.trim();
}

/**
 * Grade answer for unified exercise.
 * For Korean and Turkish, uses token-based comparison since tokens don't concatenate back to original.
 */
export function gradeUnifiedAnswer(
	langExercise: LanguageExercise,
	userTokens: string[],
	language: Language
): GradeResult {
	// For Korean and Turkish, compare token sequences directly
	// (Korean tokens don't concatenate back to original due to conjugation)
	// (Turkish words are whole tokens, not morphemes)
	if (language === 'ko' || language === 'tr') {
		const userTokensNormalized = userTokens.map(t => normalize(t));
		const expectedTokensNormalized = langExercise.tokens.map(t => normalize(t));

		// Compare token count and content
		const isCorrect =
			userTokensNormalized.length === expectedTokensNormalized.length &&
			userTokensNormalized.every((t, i) => t === expectedTokensNormalized[i]);

		return {
			correct: isCorrect,
			expected: langExercise.text,
			submitted: userTokens.join(language === 'tr' ? ' ' : '')
		};
	}

	// For Japanese and Chinese, concatenate and compare
	const userAnswer = userTokens.join('');
	const normalizedUser = normalize(userAnswer);
	const normalizedExpected = normalize(langExercise.text);

	return {
		correct: normalizedUser === normalizedExpected,
		expected: langExercise.text,
		submitted: userAnswer
	};
}

/**
 * Legacy: Grade answer client-side - no API call needed.
 * @deprecated Use gradeUnifiedAnswer instead
 */
export function gradeAnswer(exercise: Exercise, userAnswer: string): GradeResult {
	const normalizedUser = normalize(userAnswer);
	const normalizedExpected = normalize(exercise.expected);

	return {
		correct: normalizedUser === normalizedExpected,
		expected: exercise.expected,
		submitted: userAnswer
	};
}

