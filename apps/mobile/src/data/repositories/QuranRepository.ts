import AsyncStorage from "@react-native-async-storage/async-storage";
import { IQuranRepository } from "../../domain/interfaces/IQuranRepository";
import { Surah } from "../../domain/models/Surah";
import { Ayah } from "../../domain/models/Ayah";
import { Translation } from "../../domain/models/Translation";
import { QuranApiError } from "../../domain/errors/QuranApiError";
import { QuranApiClient } from "./QuranApiClient";

const CACHE_PREFIX = "quran_cache_";
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

export class QuranRepository implements IQuranRepository {
  private apiClient: QuranApiClient;

  constructor(apiClient?: QuranApiClient) {
    this.apiClient = apiClient ?? new QuranApiClient();
  }

  async getSurahs(): Promise<Surah[]> {
    const cacheKey = `${CACHE_PREFIX}surahs`;
    const cached = await this.getFromCache<Surah[]>(cacheKey);
    if (cached) return cached;

    try {
      const response = await this.apiClient.fetchChapters();
      const chapters = response.chapters as RawChapter[];
      const surahs = chapters.map(mapRawChapterToSurah);

      await this.saveToCache(cacheKey, surahs);
      return surahs;
    } catch (error) {
      if (error instanceof QuranApiError) throw error;
      throw new QuranApiError(`Failed to fetch surahs: ${error}`);
    }
  }

  async getSurah(id: number): Promise<Surah> {
    const surahs = await this.getSurahs();
    const surah = surahs.find((s) => s.id === id);
    if (!surah) {
      throw new QuranApiError(`Surah ${id} not found`);
    }
    return surah;
  }

  async getAyahs(surahId: number, translationId?: number): Promise<Ayah[]> {
    const cacheKey = translationId != null
      ? `${CACHE_PREFIX}ayahs_${surahId}_t${translationId}`
      : `${CACHE_PREFIX}ayahs_${surahId}`;
    const cached = await this.getFromCache<Ayah[]>(cacheKey);
    if (cached) return cached;

    try {
      const response = await this.apiClient.fetchVerses(surahId, 1, translationId);
      const verses = response.verses as RawVerse[];
      const ayahs = verses.map(mapRawVerseToAyah);

      await this.saveToCache(cacheKey, ayahs);
      return ayahs;
    } catch (error) {
      if (error instanceof QuranApiError) throw error;
      throw new QuranApiError(`Failed to fetch ayahs for surah ${surahId}: ${error}`);
    }
  }

  async getTranslations(): Promise<Translation[]> {
    const cacheKey = `${CACHE_PREFIX}translations_list`;
    const cached = await this.getFromCache<Translation[]>(cacheKey);
    if (cached) return cached;

    try {
      const response = await this.apiClient.fetchTranslations();
      const raw = response.translations as RawTranslation[];
      const translations = raw.map(mapRawTranslation);

      await this.saveToCache(cacheKey, translations);
      return translations;
    } catch (error) {
      if (error instanceof QuranApiError) throw error;
      throw new QuranApiError(`Failed to fetch translations: ${error}`);
    }
  }

  async getAyah(surahId: number, ayahNumber: number): Promise<Ayah> {
    const ayahs = await this.getAyahs(surahId);
    const ayah = ayahs.find((a) => a.verseNumber === ayahNumber);
    if (!ayah) {
      throw new QuranApiError(`Ayah ${ayahNumber} not found in surah ${surahId}`);
    }
    return ayah;
  }

  async clearCache(): Promise<void> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const cacheKeys = keys.filter((key) => key.startsWith(CACHE_PREFIX));
      if (cacheKeys.length > 0) {
        await AsyncStorage.multiRemove(cacheKeys);
      }
    } catch (error) {
      throw new QuranApiError(`Failed to clear cache: ${error}`);
    }
  }

  private async getFromCache<T>(key: string): Promise<T | null> {
    try {
      const raw = await AsyncStorage.getItem(key);
      if (!raw) return null;

      const entry: CacheEntry<T> = JSON.parse(raw);
      if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
        await AsyncStorage.removeItem(key);
        return null;
      }

      return entry.data;
    } catch {
      return null;
    }
  }

  private async saveToCache<T>(key: string, data: T): Promise<void> {
    try {
      const entry: CacheEntry<T> = { data, timestamp: Date.now() };
      await AsyncStorage.setItem(key, JSON.stringify(entry));
    } catch {
      // Cache write failures are non-critical
    }
  }
}

interface RawChapter {
  id: number;
  revelation_place: string;
  revelation_order: number;
  bismillah_pre: boolean;
  name_simple: string;
  name_complex: string;
  name_arabic: string;
  verses_count: number;
  pages: number[];
  translated_name: {
    language_name: string;
    name: string;
  };
}

interface RawVerse {
  id: number;
  verse_number: number;
  verse_key: string;
  hizb_number: number;
  rub_el_hizb_number: number;
  riku_number: number;
  juz_number: number;
  text_uthmani: string;
  text_imlaei: string;
  translations?: { text: string }[];
}

interface RawTranslation {
  id: number;
  name: string;
  author_name: string;
  language_name: string;
}

function mapRawChapterToSurah(raw: RawChapter): Surah {
  return {
    id: raw.id,
    revelationPlace: raw.revelation_place,
    revelationOrder: raw.revelation_order,
    bismillahPre: raw.bismillah_pre,
    nameSimple: raw.name_simple,
    nameComplex: raw.name_complex,
    nameArabic: raw.name_arabic,
    versesCount: raw.verses_count,
    pages: raw.pages,
    translatedName: {
      languageName: raw.translated_name.language_name,
      name: raw.translated_name.name,
    },
  };
}

function stripHtml(text: string): string {
  return text.replace(/<[^>]*>/g, "");
}

function mapRawVerseToAyah(raw: RawVerse): Ayah {
  const ayah: Ayah = {
    id: raw.id,
    verseNumber: raw.verse_number,
    verseKey: raw.verse_key,
    hizbNumber: raw.hizb_number,
    rubElHizbNumber: raw.rub_el_hizb_number,
    rpiPageNumber: raw.riku_number,
    juzNumber: raw.juz_number,
    textUthmani: raw.text_uthmani,
    textSimple: raw.text_imlaei,
  };
  if (raw.translations?.[0]?.text) {
    ayah.translation = stripHtml(raw.translations[0].text);
  }
  return ayah;
}

function mapRawTranslation(raw: RawTranslation): Translation {
  return {
    id: raw.id,
    name: raw.name,
    authorName: raw.author_name,
    languageName: raw.language_name,
  };
}

export const quranRepository = new QuranRepository();
