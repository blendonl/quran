import { TranscriptionSegment } from "../models/TranscriptionSegment";
import { ElongationResult } from "../models/ElongationResult";

export interface ElongationSettings {
  thresholdMs: number;
  baseUnitMs: number;
  maxRepetitions: number;
}

export interface IElongationDetector {
  detect(segments: TranscriptionSegment[], settings?: Partial<ElongationSettings>): ElongationResult;
}
