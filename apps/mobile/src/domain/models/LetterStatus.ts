export type LetterStatusValue = "CORRECT" | "INCORRECT" | "NOT_SURE";

export interface LetterStatusUpdate {
  surahId: number;
  ayahNumber: number;
  updates: Array<{
    wordIndex: number;
    letterIndex: number;
    status: LetterStatusValue;
  }>;
  confidence: number;
}
