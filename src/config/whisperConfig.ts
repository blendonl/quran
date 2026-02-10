import { WhisperModelInfo } from "../domain/models/WhisperModel";

export const WHISPER_TRANSCRIPTION_OPTIONS = {
  language: "ar",
  tokenTimestamps: true,
  maxLen: 1,
  temperature: 0.0,
  beamSize: 5,
} as const;

export const TARTEEL_QURAN_MODEL: WhisperModelInfo = {
  name: "tarteel-whisper-base-ar-quran",
  fileName: "ggml-tarteel-base-ar-quran-q5_1.bin",
  sizeBytes: 57 * 1024 * 1024,
  downloadUrl:
    "https://huggingface.co/tarteel-ai/whisper-base-ar-quran/resolve/main/ggml-model-q5_1.bin",
  status: "not_downloaded",
  downloadProgress: 0,
};

export const FALLBACK_WHISPER_MODEL: WhisperModelInfo = {
  name: "ggml-base",
  fileName: "ggml-base.bin",
  sizeBytes: 142 * 1024 * 1024,
  downloadUrl:
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
  status: "not_downloaded",
  downloadProgress: 0,
};
