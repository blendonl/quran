import { initWhisper, WhisperContext } from "whisper.rn";
import {
  ISpeechRecognitionService,
  TranscriptionOptions,
  TranscriptionResponse,
} from "../../domain/interfaces/ISpeechRecognitionService";
import { TranscriptionSegment } from "../../domain/models/TranscriptionSegment";
import { WhisperInitError } from "../../domain/errors/WhisperInitError";
import { TranscriptionError } from "../../domain/errors/TranscriptionError";
import { WHISPER_TRANSCRIPTION_OPTIONS } from "../../config/whisperConfig";
import { WhisperModelManager } from "./WhisperModelManager";

export class WhisperService implements ISpeechRecognitionService {
  private context: WhisperContext | null = null;
  private modelManager: WhisperModelManager;
  private ready = false;

  constructor(modelManager: WhisperModelManager) {
    this.modelManager = modelManager;
  }

  async initialize(): Promise<void> {
    try {
      const modelPath = await this.modelManager.downloadModelWithFallback();

      this.context = await initWhisper({
        filePath: modelPath,
      });

      this.ready = true;
    } catch (error) {
      this.ready = false;
      throw new WhisperInitError(`Failed to initialize Whisper: ${error}`);
    }
  }

  async transcribe(
    audioFilePath: string,
    options: TranscriptionOptions,
  ): Promise<TranscriptionResponse> {
    if (!this.context || !this.ready) {
      throw new TranscriptionError("Whisper context not initialized. Call initialize() first.");
    }

    try {
      const { promise } = this.context.transcribe(audioFilePath, {
        ...WHISPER_TRANSCRIPTION_OPTIONS,
        language: options.language,
        prompt: options.prompt,
      });

      const result = await promise;

      const segments: TranscriptionSegment[] = (result.segments || []).map((seg) => ({
        text: seg.text.trim(),
        t0: seg.t0,
        t1: seg.t1,
        confidence: 1.0,
      }));

      return {
        text: result.result,
        segments,
      };
    } catch (error) {
      throw new TranscriptionError(`Transcription failed: ${error}`);
    }
  }

  isReady(): boolean {
    return this.ready;
  }

  async release(): Promise<void> {
    try {
      if (this.context) {
        await this.context.release();
        this.context = null;
        this.ready = false;
      }
    } catch (error) {
      throw new WhisperInitError(`Failed to release Whisper context: ${error}`);
    }
  }

  getContext(): WhisperContext | null {
    return this.context;
  }
}
