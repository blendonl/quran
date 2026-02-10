import {
  isElongatable,
  isMaddLetter,
  isGhunnaLetter,
  getElongationCategory,
  stripDiacritics,
  extractBaseLetters,
} from "../services/elongation/ArabicPhonemeMap";

describe("ArabicPhonemeMap", () => {
  describe("isElongatable", () => {
    it("should return true for madd letters", () => {
      expect(isElongatable("ا")).toBe(true);
      expect(isElongatable("و")).toBe(true);
      expect(isElongatable("ي")).toBe(true);
    });

    it("should return true for ghunna letters", () => {
      expect(isElongatable("م")).toBe(true);
      expect(isElongatable("ن")).toBe(true);
    });

    it("should return true for holdable consonants", () => {
      expect(isElongatable("س")).toBe(true);
      expect(isElongatable("ش")).toBe(true);
      expect(isElongatable("ف")).toBe(true);
    });

    it("should return false for non-elongatable letters", () => {
      expect(isElongatable("ب")).toBe(false);
      expect(isElongatable("ت")).toBe(false);
      expect(isElongatable("ك")).toBe(false);
    });
  });

  describe("getElongationCategory", () => {
    it("should categorize madd letters", () => {
      expect(getElongationCategory("ا")).toBe("madd");
    });

    it("should categorize ghunna letters", () => {
      expect(getElongationCategory("م")).toBe("ghunna");
    });

    it("should categorize holdable consonants", () => {
      expect(getElongationCategory("س")).toBe("holdable");
    });

    it("should return none for non-elongatable", () => {
      expect(getElongationCategory("ب")).toBe("none");
    });
  });

  describe("stripDiacritics", () => {
    it("should remove all tashkeel marks", () => {
      expect(stripDiacritics("بِسْمِ")).toBe("بسم");
    });

    it("should remove tatweel", () => {
      expect(stripDiacritics("اللـه")).toBe("الله");
    });
  });

  describe("extractBaseLetters", () => {
    it("should extract clean letters from text with diacritics", () => {
      const letters = extractBaseLetters("بِسْمِ");
      expect(letters).toEqual(["ب", "س", "م"]);
    });
  });
});
