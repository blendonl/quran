export type TajweedGrade = "excellent" | "good" | "needs_work" | "missed";

export type TajweedRule =
  | "idghaam_bi_ghunnah"
  | "idghaam_bila_ghunnah"
  | "ikhfaa"
  | "iqlab"
  | "izhar"
  | "madd_natural"
  | "madd_connected"
  | "madd_separated"
  | "madd_secondary"
  | "ghunnah"
  | "qalqalah";

export interface TajweedGradeUpdate {
  surahId: number;
  ayahNumber: number;
  updates: Array<{
    wordIndex: number;
    letterIndex: number;
    rule: TajweedRule;
    grade: TajweedGrade;
  }>;
}
