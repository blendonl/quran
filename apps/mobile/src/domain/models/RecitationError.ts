export interface RecitationErrorDetail {
  errorType: string;
  speechErrorType: string;
  expectedPhoneme: string;
  predictedPhoneme: string;
  uthmaniStart: number;
  uthmaniEnd: number;
  tajweedRule: string | null;
  expectedLen: number | null;
  predictedLen: number | null;
}

export interface RecitationErrorUpdate {
  surahId: number;
  ayahNumber: number;
  errors: RecitationErrorDetail[];
}
