export type WhisperModelStatus = "not_downloaded" | "downloading" | "ready" | "error";

export interface WhisperModelInfo {
  name: string;
  fileName: string;
  sizeBytes: number;
  downloadUrl: string;
  status: WhisperModelStatus;
  downloadProgress: number;
  localPath?: string;
}
