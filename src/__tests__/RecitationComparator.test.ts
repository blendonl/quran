import { RecitationComparator } from "../services/comparison/RecitationComparator";

describe("RecitationComparator", () => {
  const comparator = new RecitationComparator();

  it("should return 100% accuracy for perfect recitation", () => {
    const text = "بسم الله الرحمن الرحيم";
    const result = comparator.compare(text, text);
    expect(result.accuracy).toBe(1);
    expect(result.wordMatches.every((m) => m.status === "correct")).toBe(true);
  });

  it("should detect incorrect words", () => {
    const recited = "بسم الله الرحمن الكريم";
    const expected = "بسم الله الرحمن الرحيم";
    const result = comparator.compare(recited, expected);
    expect(result.accuracy).toBeLessThan(1);
    const incorrect = result.wordMatches.filter((m) => m.status === "incorrect");
    expect(incorrect.length).toBeGreaterThan(0);
  });

  it("should detect missing words", () => {
    const recited = "بسم الله الرحيم";
    const expected = "بسم الله الرحمن الرحيم";
    const result = comparator.compare(recited, expected);
    const missing = result.wordMatches.filter((m) => m.status === "missing");
    expect(missing.length).toBeGreaterThan(0);
  });

  it("should detect extra words", () => {
    const recited = "بسم الله العظيم الرحمن الرحيم";
    const expected = "بسم الله الرحمن الرحيم";
    const result = comparator.compare(recited, expected);
    const extra = result.wordMatches.filter((m) => m.status === "extra");
    expect(extra.length).toBeGreaterThan(0);
  });

  it("should handle empty recitation", () => {
    const result = comparator.compare("", "بسم الله");
    expect(result.accuracy).toBe(0);
    expect(result.wordMatches.every((m) => m.status === "missing")).toBe(true);
  });

  it("should handle empty expected text", () => {
    const result = comparator.compare("بسم الله", "");
    expect(result.accuracy).toBe(1);
  });

  it("should calculate correct accuracy percentage", () => {
    const recited = "بسم الله الرحمن";
    const expected = "بسم الله الرحمن الرحيم";
    const result = comparator.compare(recited, expected);
    expect(result.accuracy).toBe(0.75);
  });
});
