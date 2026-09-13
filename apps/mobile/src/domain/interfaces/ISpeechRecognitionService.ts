import { TranscriptionSegment } from "../models/TranscriptionSegment";

export interface TranscriptionOptions {
  language: string;
  prompt?: string;
}

export interface TranscriptionResponse {
  text: string;
  segments: TranscriptionSegment[];
}

export interface ISpeechRecognitionService {
  initialize(): Promise<void>;
  transcribe(audioFilePath: string, options: TranscriptionOptions): Promise<TranscriptionResponse>;
  isReady(): boolean;
  release(): Promise<void>;
}
