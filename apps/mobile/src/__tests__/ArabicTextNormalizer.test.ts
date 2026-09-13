import { ArabicTextNormalizer } from "../services/comparison/ArabicTextNormalizer";

describe("ArabicTextNormalizer", () => {
  const normalizer = new ArabicTextNormalizer();

  it("should strip tashkeel (diacritics)", () => {
    const input = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ";
    const result = normalizer.stripTashkeel(input);
    expect(result).not.toContain("\u0650");
    expect(result).not.toContain("\u064E");
    expect(result).not.toContain("\u0651");
  });

  it("should normalize hamza variants to bare alef", () => {
    expect(normalizer.normalizeHamza("أحمد")).toBe("احمد");
    expect(normalizer.normalizeHamza("إبراهيم")).toBe("ابراهيم");
    expect(normalizer.normalizeHamza("آمين")).toBe("امين");
  });

  it("should normalize ta marbuta to ha", () => {
    expect(normalizer.normalizeTaMarbuta("رحمة")).toBe("رحمه");
  });

  it("should normalize alef maksura to ya", () => {
    expect(normalizer.normalizeAlefMaksura("على")).toBe("علي");
  });

  it("should normalize complete text", () => {
    const input = "بِسْمِ اللَّهِ";
    const result = normalizer.normalize(input);
    expect(result).not.toMatch(/[\u064B-\u0652]/);
    expect(result.trim().length).toBeGreaterThan(0);
  });

  it("should split into normalized words", () => {
    const input = "بِسْمِ اللَّهِ الرَّحْمَٰنِ";
    const words = normalizer.splitIntoWords(input);
    expect(words.length).toBe(3);
  });

  it("should collapse multiple spaces", () => {
    const result = normalizer.normalize("بسم   الله");
    expect(result).toBe("بسم الله");
  });
});
