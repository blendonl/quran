import { Paths, File, Directory } from "expo-file-system";
import { WhisperModelInfo, WhisperModelStatus } from "../../domain/models/WhisperModel";
import { ModelDownloadError } from "../../domain/errors/ModelDownloadError";
import { TARTEEL_QURAN_MODEL, FALLBACK_WHISPER_MODEL } from "../../config/whisperConfig";

export type DownloadProgressCallback = (progress: number) => void;

export class WhisperModelManager {
  private modelDir: Directory;

  constructor() {
    this.modelDir = new Directory(Paths.document, "whisper-models");
  }

  getModelPath(model: WhisperModelInfo = TARTEEL_QURAN_MODEL): string {
    const file = new File(this.modelDir, model.fileName);
    return file.uri;
  }

  isModelDownloaded(model: WhisperModelInfo = TARTEEL_QURAN_MODEL): boolean {
    try {
      const file = new File(this.modelDir, model.fileName);
      return file.exists;
    } catch {
      return false;
    }
  }

  async downloadModel(
    model: WhisperModelInfo = TARTEEL_QURAN_MODEL,
    onProgress?: DownloadProgressCallback,
  ): Promise<string> {
    try {
      if (!this.modelDir.exists) {
        this.modelDir.create({ intermediates: true });
      }

      const modelFile = new File(this.modelDir, model.fileName);

      if (modelFile.exists) {
        onProgress?.(1);
        return modelFile.uri;
      }

      onProgress?.(0.01);

      const downloaded = await File.downloadFileAsync(model.downloadUrl, modelFile, {
        idempotent: true,
      });

      onProgress?.(1);

      return downloaded.uri;
    } catch (error) {
      if (error instanceof ModelDownloadError) throw error;
      throw new ModelDownloadError(`Failed to download model: ${error}`);
    }
  }

  async downloadModelWithFallback(onProgress?: DownloadProgressCallback): Promise<string> {
    try {
      return await this.downloadModel(TARTEEL_QURAN_MODEL, onProgress);
    } catch {
      return await this.downloadModel(FALLBACK_WHISPER_MODEL, onProgress);
    }
  }

  deleteModel(model: WhisperModelInfo = TARTEEL_QURAN_MODEL): void {
    try {
      const file = new File(this.modelDir, model.fileName);
      if (file.exists) {
        file.delete();
      }
    } catch (error) {
      throw new ModelDownloadError(`Failed to delete model: ${error}`);
    }
  }

  getModelStatus(model: WhisperModelInfo = TARTEEL_QURAN_MODEL): WhisperModelStatus {
    return this.isModelDownloaded(model) ? "ready" : "not_downloaded";
  }
}
