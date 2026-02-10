import { IElongationDetector, ElongationSettings } from "../../domain/interfaces/IElongationDetector";
import { TranscriptionSegment } from "../../domain/models/TranscriptionSegment";
import { ElongationResult, ElongatedCharacter } from "../../domain/models/ElongationResult";
import { DEFAULT_ELONGATION_SETTINGS } from "../../config/elongationConfig";
import { isElongatable, stripDiacritics } from "./ArabicPhonemeMap";

export class ElongationDetector implements IElongationDetector {
  detect(
    segments: TranscriptionSegment[],
    settings?: Partial<ElongationSettings>,
  ): ElongationResult {
    const config: ElongationSettings = {
      ...DEFAULT_ELONGATION_SETTINGS,
      ...settings,
    };

    const characters: ElongatedCharacter[] = [];
    let displayText = "";
    let originalText = "";

    for (const segment of segments) {
      const durationMs = (segment.t1 - segment.t0) * 10;
      const cleanText = stripDiacritics(segment.text);

      for (const char of cleanText) {
        if (char.trim().length === 0) {
          characters.push({
            original: char,
            displayed: char,
            repetitions: 1,
            durationMs: 0,
            isElongated: false,
          });
          displayText += char;
          originalText += char;
          continue;
        }

        const elongatable = isElongatable(char);
        let repetitions = 1;

        if (elongatable && durationMs > config.thresholdMs) {
          repetitions = Math.round(durationMs / config.baseUnitMs);
          repetitions = Math.max(1, Math.min(repetitions, config.maxRepetitions));
        }

        const displayed = char.repeat(repetitions);

        characters.push({
          original: char,
          displayed,
          repetitions,
          durationMs,
          isElongated: repetitions > 1,
        });

        displayText += displayed;
        originalText += char;
      }
    }

    return {
      originalText,
      displayText,
      characters,
    };
  }
}
