/** Supported languages */
export type Language = 'ja' | 'zh' | 'ko' | 'tr';

/** Language display info */
export interface LanguageInfo {
	code: Language;
	name: string;
	flag: string;
	nativeName: string;
}

export const LANGUAGES: LanguageInfo[] = [
	{ code: 'ja', name: 'Japanese', flag: '🇯🇵', nativeName: '日本語' },
	{ code: 'zh', name: 'Chinese', flag: '🇨🇳', nativeName: '中文' },
	{ code: 'ko', name: 'Korean', flag: '🇰🇷', nativeName: '한국어' },
	{ code: 'tr', name: 'Turkish', flag: '🇹🇷', nativeName: 'Türkçe' }
];

/** Tile as received from the API */
export interface ApiTile {
	id: number;
	text: string;
}

/** Tile with stable unique ID for drag-and-drop */
export interface TileData {
	id: string;           // Unique stable ID (e.g., "tile-0", "tile-1")
	text: string;         // The target language text to display
	originalIndex: number; // Original position from API (for reference)
}

/** Exercise data for a single language */
export interface LanguageExercise {
	text: string;          // Target sentence in this language
	tokens: string[];      // Correct tokens in order (for grading)
	tiles: ApiTile[];      // Shuffled tiles (correct + distractors)
	num_correct_tiles: number;
}

/** Unified exercise with all language translations */
export interface UnifiedExercise {
	exercise_id: number;
	english: string;
	exercises: Partial<Record<Language, LanguageExercise>>;
}

/** Legacy single-language exercise (kept for compatibility) */
export interface Exercise {
	exercise_id: number;
	english: string;
	tiles: ApiTile[];
	num_correct_tiles: number;
	language?: Language;
	expected: string;  // Correct answer for client-side grading
}

export interface GradeResult {
	correct: boolean;
	expected: string;
	submitted: string;
}

