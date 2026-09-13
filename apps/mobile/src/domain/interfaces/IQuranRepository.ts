import { Surah } from "../models/Surah";
import { Ayah } from "../models/Ayah";
import { Translation } from "../models/Translation";

export interface IQuranRepository {
  getSurahs(): Promise<Surah[]>;
  getSurah(id: number): Promise<Surah>;
  getAyahs(surahId: number, translationId?: number): Promise<Ayah[]>;
  getAyah(surahId: number, ayahNumber: number): Promise<Ayah>;
  getTranslations(): Promise<Translation[]>;
  clearCache(): Promise<void>;
}
