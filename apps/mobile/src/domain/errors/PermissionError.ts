import { AppError } from "./AppError";

export class PermissionError extends AppError {
  constructor(message: string) {
    super(message, "PERMISSION_ERROR");
  }
}
