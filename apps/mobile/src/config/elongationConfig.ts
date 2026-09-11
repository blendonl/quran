import { ElongationSettings } from "../domain/interfaces/IElongationDetector";

export const DEFAULT_ELONGATION_SETTINGS: ElongationSettings = {
  thresholdMs: 200,
  baseUnitMs: 150,
  maxRepetitions: 8,
};
