import { ElongationDetector } from "../services/elongation/ElongationDetector";
import { TranscriptionSegment } from "../domain/models/TranscriptionSegment";

describe("ElongationDetector", () => {
  const detector = new ElongationDetector();

  it("should detect elongation for madd letter with long duration", () => {
    const segments: TranscriptionSegment[] = [
      { text: "ا", t0: 100, t1: 135, confidence: 1 },
    ];

    const result = detector.detect(segments);

    const elongatedChar = result.characters.find((c) => c.original === "ا");
    expect(elongatedChar?.isElongated).toBe(true);
    expect(elongatedChar!.repetitions).toBeGreaterThan(1);
  });

  it("should not elongate letters with short duration", () => {
    const segments: TranscriptionSegment[] = [
      { text: "ب", t0: 100, t1: 110, confidence: 1 },
    ];

    const result = detector.detect(segments);

    expect(result.characters[0].isElongated).toBe(false);
    expect(result.characters[0].repetitions).toBe(1);
  });

  it("should not elongate non-elongatable letters even with long duration", () => {
    const segments: TranscriptionSegment[] = [
      { text: "ب", t0: 100, t1: 150, confidence: 1 },
    ];

    const result = detector.detect(segments);

    expect(result.characters[0].isElongated).toBe(false);
  });

  it("should respect maxRepetitions setting", () => {
    const segments: TranscriptionSegment[] = [
      { text: "ا", t0: 0, t1: 500, confidence: 1 },
    ];

    const result = detector.detect(segments, { maxRepetitions: 3 });

    const elongatedChar = result.characters.find((c) => c.original === "ا");
    expect(elongatedChar!.repetitions).toBeLessThanOrEqual(3);
  });

  it("should handle multiple segments correctly", () => {
    const segments: TranscriptionSegment[] = [
      { text: "ب", t0: 0, t1: 10, confidence: 1 },
      { text: "ا", t0: 10, t1: 45, confidence: 1 },
      { text: "ن", t0: 45, t1: 80, confidence: 1 },
    ];

    const result = detector.detect(segments);

    expect(result.characters).toHaveLength(3);
    expect(result.characters[0].original).toBe("ب");
    expect(result.characters[1].original).toBe("ا");
    expect(result.characters[2].original).toBe("ن");
  });

  it("should calculate correct duration in ms", () => {
    const segments: TranscriptionSegment[] = [
      { text: "ا", t0: 150, t1: 185, confidence: 1 },
    ];

    const result = detector.detect(segments);

    expect(result.characters[0].durationMs).toBe(350);
  });

  it("should strip diacritics from input", () => {
    const segments: TranscriptionSegment[] = [
      { text: "بِ", t0: 0, t1: 10, confidence: 1 },
    ];

    const result = detector.detect(segments);

    expect(result.characters[0].original).toBe("ب");
  });
});
