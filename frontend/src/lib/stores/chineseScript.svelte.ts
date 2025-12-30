/**
 * Store for Chinese script preference (Simplified vs Traditional)
 * Only relevant when the language is set to Chinese (zh)
 */
import { browser } from '$app/environment';

export type ChineseScript = 'simplified' | 'traditional';

const STORAGE_KEY = 'chineseScript';
const DEFAULT_SCRIPT: ChineseScript = 'simplified';

function createChineseScriptStore() {
	let value = $state<ChineseScript>(DEFAULT_SCRIPT);

	// Load from localStorage on init (browser only)
	if (browser) {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored === 'simplified' || stored === 'traditional') {
			value = stored;
		}
	}

	return {
		get value() {
			return value;
		},
		set(newValue: ChineseScript) {
			value = newValue;
			if (browser) {
				localStorage.setItem(STORAGE_KEY, newValue);
			}
		},
		toggle() {
			const newValue = value === 'simplified' ? 'traditional' : 'simplified';
			this.set(newValue);
		}
	};
}

export const chineseScriptStore = createChineseScriptStore();

