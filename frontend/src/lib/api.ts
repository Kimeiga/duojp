import type { Exercise, GradeResult, Language } from './types';

const API_BASE = '/api';

export async function fetchExercise(language: Language = 'ja'): Promise<Exercise> {
	const res = await fetch(`${API_BASE}/exercise?lang=${language}`);
	if (!res.ok) throw new Error('Failed to fetch exercise');
	return res.json();
}

/**
 * Grade answer client-side - no API call needed.
 * Compares user's answer with the expected answer from the exercise.
 */
export function gradeAnswer(exercise: Exercise, userAnswer: string): GradeResult {
	// Normalize both strings for comparison (remove spaces, convert to lowercase for comparison)
	const normalize = (s: string) => s.replace(/\s+/g, '').trim();
	const normalizedUser = normalize(userAnswer);
	const normalizedExpected = normalize(exercise.expected);

	return {
		correct: normalizedUser === normalizedExpected,
		expected: exercise.expected,
		submitted: userAnswer
	};
}

