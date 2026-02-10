import { AppError } from "./AppError";

export class QuranApiError extends AppError {
  constructor(message: string) {
    super(message, "QURAN_API_ERROR");
  }
}
