import { browser } from '$app/environment';
import type { Language } from '$lib/types';

const STORAGE_KEY = 'selectedLanguage';
const DEFAULT_LANGUAGE: Language = 'ja';

// Create a simple reactive store for language
function createLanguageStore() {
	let currentLanguage = $state<Language>(DEFAULT_LANGUAGE);

	// Initialize from localStorage on browser
	if (browser) {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored === 'ja' || stored === 'zh' || stored === 'ko' || stored === 'tr') {
			currentLanguage = stored;
		}
	}

	return {
		get value() {
			return currentLanguage;
		},
		set(lang: Language) {
			currentLanguage = lang;
			if (browser) {
				localStorage.setItem(STORAGE_KEY, lang);
			}
		}
	};
}

export const languageStore = createLanguageStore();

