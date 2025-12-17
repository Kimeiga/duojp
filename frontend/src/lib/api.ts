import type { Exercise, GradeResult } from './types';

const API_BASE = '/api';

export async function fetchExercise(): Promise<Exercise> {
	const res = await fetch(`${API_BASE}/exercise`);
	if (!res.ok) throw new Error('Failed to fetch exercise');
	return res.json();
}

export async function gradeAnswer(exerciseId: number, answer: string): Promise<GradeResult> {
	const res = await fetch(`${API_BASE}/grade`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ exercise_id: exerciseId, answer })
	});
	if (!res.ok) throw new Error('Failed to grade answer');
	return res.json();
}

