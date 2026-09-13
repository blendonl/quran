const MADD_LETTERS = new Set(["ا", "و", "ي"]);

const GHUNNA_LETTERS = new Set(["م", "ن"]);

const HOLDABLE_CONSONANTS = new Set(["س", "ص", "ش", "ف", "ث", "ذ", "ز", "ظ", "ر", "ل", "ه"]);

const ALL_ELONGATABLE = new Set([...MADD_LETTERS, ...GHUNNA_LETTERS, ...HOLDABLE_CONSONANTS]);

export function isElongatable(char: string): boolean {
  return ALL_ELONGATABLE.has(char);
}

export function isMaddLetter(char: string): boolean {
  return MADD_LETTERS.has(char);
}

export function isGhunnaLetter(char: string): boolean {
  return GHUNNA_LETTERS.has(char);
}

export function isHoldableConsonant(char: string): boolean {
  return HOLDABLE_CONSONANTS.has(char);
}

export function getElongationCategory(char: string): "madd" | "ghunna" | "holdable" | "none" {
  if (MADD_LETTERS.has(char)) return "madd";
  if (GHUNNA_LETTERS.has(char)) return "ghunna";
  if (HOLDABLE_CONSONANTS.has(char)) return "holdable";
  return "none";
}

export function stripDiacritics(text: string): string {
  return text.replace(/[\u064B-\u0652\u0670\u0640]/g, "");
}

export function extractBaseLetters(text: string): string[] {
  return stripDiacritics(text).split("").filter((c) => c.trim().length > 0);
}
