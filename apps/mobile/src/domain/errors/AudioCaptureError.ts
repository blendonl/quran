import { AppError } from "./AppError";

export class AudioCaptureError extends AppError {
  constructor(message: string) {
    super(message, "AUDIO_CAPTURE_ERROR");
  }
}
