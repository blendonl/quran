export type WordStatusValue = "ALIGNED" | "CORRECT" | "INCORRECT" | "NOT_SURE";

export interface WordStatusUpdate {
  surahId: number;
  ayahNumber: number;
  updates: Array<{
    wordIndex: number;
    status: WordStatusValue;
    confidence: number;
    tajweedGrade: string | null;
  }>;
}
