import { AppError } from "./AppError";

export class WhisperInitError extends AppError {
  constructor(message: string) {
    super(message, "WHISPER_INIT_ERROR");
  }
}
