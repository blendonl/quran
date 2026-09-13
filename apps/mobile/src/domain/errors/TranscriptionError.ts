import { AppError } from "./AppError";

export class TranscriptionError extends AppError {
  constructor(message: string) {
    super(message, "TRANSCRIPTION_ERROR");
  }
}
