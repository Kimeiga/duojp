/** Tile as received from the API */
export interface ApiTile {
	id: number;
	text: string;
}

/** Tile with stable unique ID for drag-and-drop */
export interface TileData {
	id: string;           // Unique stable ID (e.g., "tile-0", "tile-1")
	text: string;         // The Japanese text to display
	originalIndex: number; // Original position from API (for reference)
}

export interface Exercise {
	exercise_id: number;
	english: string;
	tiles: ApiTile[];
	num_correct_tiles: number;
}

export interface GradeResult {
	correct: boolean;
	expected: string;
	submitted: string;
}

