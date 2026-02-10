export type WordMatchStatus = "correct" | "incorrect" | "missing" | "extra";

export interface WordMatch {
  word: string;
  status: WordMatchStatus;
  expectedWord?: string;
}

export interface RecitationResult {
  recitedText: string;
  expectedText: string;
  wordMatches: WordMatch[];
  accuracy: number;
}
