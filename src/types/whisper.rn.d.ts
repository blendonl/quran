declare module "whisper.rn" {
  export interface ContextOptions {
    filePath: string | number;
    coreMLModelAsset?: {
      filename: string;
      assets: string[] | number[];
    };
    isBundleAsset?: boolean;
    useCoreMLIos?: boolean;
    useGpu?: boolean;
    useFlashAttn?: boolean;
  }

  export interface TranscribeOptions {
    language?: string;
    translate?: boolean;
    maxThreads?: number;
    maxContext?: number;
    maxLen?: number;
    tokenTimestamps?: boolean;
    wordThold?: number;
    offset?: number;
    duration?: number;
    temperature?: number;
    temperatureInc?: number;
    beamSize?: number;
    bestOf?: number;
    prompt?: string;
  }

  export interface TranscribeResult {
    result: string;
    language: string;
    isAborted: boolean;
    segments: Array<{
      text: string;
      t0: number;
      t1: number;
    }>;
  }

  export interface TranscribeRealtimeOptions extends TranscribeOptions {
    realtimeAudioSec?: number;
    realtimeAudioSliceSec?: number;
    realtimeAudioMinSec?: number;
    audioOutputPath?: string;
    useVad?: boolean;
    vadMs?: number;
    vadThold?: number;
    vadFreqThold?: number;
  }

  export interface TranscribeRealtimeEvent {
    contextId: number;
    jobId: number;
    isCapturing: boolean;
    isStoppedByAction?: boolean;
    code: number;
    data?: TranscribeResult;
    error?: string;
    processTime: number;
    recordingTime: number;
    slices?: Array<{
      code: number;
      error?: string;
      data?: TranscribeResult;
      processTime: number;
      recordingTime: number;
    }>;
  }

  export class WhisperContext {
    id: number;
    gpu: boolean;
    reasonNoGPU: string;

    transcribe(
      filePathOrBase64: string | number,
      options?: TranscribeOptions,
    ): {
      stop: () => Promise<void>;
      promise: Promise<TranscribeResult>;
    };

    transcribeRealtime(
      options?: TranscribeRealtimeOptions,
    ): Promise<{
      stop: () => Promise<void>;
      subscribe: (callback: (event: TranscribeRealtimeEvent) => void) => void;
    }>;

    release(): Promise<void>;
  }

  export function initWhisper(options: ContextOptions): Promise<WhisperContext>;
  export function releaseAllWhisper(): Promise<void>;
}
