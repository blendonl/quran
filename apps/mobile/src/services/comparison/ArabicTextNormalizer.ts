const TASHKEEL_REGEX = /[\u064B-\u0652\u0670\u0640]/g;

const HAMZA_MAP: Record<string, string> = {
  "\u0622": "\u0627", // آ → ا
  "\u0623": "\u0627", // أ → ا
  "\u0625": "\u0627", // إ → ا
  "\u0671": "\u0627", // ٱ → ا
};

const TA_MARBUTA = "\u0629"; // ة
const HA = "\u0647"; // ه

const ALEF_MAKSURA = "\u0649"; // ى
const YA = "\u064A"; // ي

export class ArabicTextNormalizer {
  normalize(text: string): string {
    let normalized = this.stripTashkeel(text);
    normalized = this.normalizeHamza(normalized);
    normalized = this.normalizeTaMarbuta(normalized);
    normalized = this.normalizeAlefMaksura(normalized);
    normalized = normalized.trim().replace(/\s+/g, " ");
    return normalized;
  }

  stripTashkeel(text: string): string {
    return text.replace(TASHKEEL_REGEX, "");
  }

  normalizeHamza(text: string): string {
    let result = text;
    for (const [from, to] of Object.entries(HAMZA_MAP)) {
      result = result.replaceAll(from, to);
    }
    return result;
  }

  normalizeTaMarbuta(text: string): string {
    return text.replaceAll(TA_MARBUTA, HA);
  }

  normalizeAlefMaksura(text: string): string {
    return text.replaceAll(ALEF_MAKSURA, YA);
  }

  splitIntoWords(text: string): string[] {
    return this.normalize(text)
      .split(/\s+/)
      .filter((w) => w.length > 0);
  }
}
