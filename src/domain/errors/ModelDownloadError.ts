import { AppError } from "./AppError";

export class ModelDownloadError extends AppError {
  constructor(message: string) {
    super(message, "MODEL_DOWNLOAD_ERROR");
  }
}
