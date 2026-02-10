import { Surah } from "../models/Surah";
import { Ayah } from "../models/Ayah";

export interface IQuranRepository {
  getSurahs(): Promise<Surah[]>;
  getSurah(id: number): Promise<Surah>;
  getAyahs(surahId: number): Promise<Ayah[]>;
  getAyah(surahId: number, ayahNumber: number): Promise<Ayah>;
  clearCache(): Promise<void>;
}
