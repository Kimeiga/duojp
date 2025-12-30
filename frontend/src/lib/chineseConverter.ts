/**
 * Chinese Simplified <-> Traditional converter
 * Uses opencc-js for accurate conversion
 */
import * as OpenCC from 'opencc-js';
import type { ChineseScript } from './stores/chineseScript.svelte';

// Create converter: Simplified Chinese (Mainland) -> Traditional Chinese (Taiwan)
const s2tConverter = OpenCC.Converter({ from: 'cn', to: 'tw' });

/**
 * Convert Chinese text based on the target script.
 * Data is stored in Simplified Chinese, so:
 * - If target is 'simplified', return as-is
 * - If target is 'traditional', convert to Traditional
 */
export function convertChinese(text: string, targetScript: ChineseScript): string {
	if (targetScript === 'simplified') {
		return text;
	}
	return s2tConverter(text);
}

