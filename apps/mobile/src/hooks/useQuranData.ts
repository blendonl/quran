import { useState, useCallback } from "react";
import { Surah } from "../domain/models/Surah";
import { Ayah } from "../domain/models/Ayah";
import { quranRepository } from "../data/repositories/QuranRepository";

export function useQuranData() {
  const [surahs, setSurahs] = useState<Surah[]>([]);
  const [ayahs, setAyahs] = useState<Ayah[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSurahs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await quranRepository.getSurahs();
      setSurahs(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load surahs");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadAyahs = useCallback(async (surahId: number, translationId?: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await quranRepository.getAyahs(surahId, translationId);
      setAyahs(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load ayahs");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    surahs,
    ayahs,
    isLoading,
    error,
    loadSurahs,
    loadAyahs,
  };
}
