import { useState, useCallback, useRef } from "react";
import { Surah } from "../domain/models/Surah";
import { Ayah } from "../domain/models/Ayah";
import { QuranRepository } from "../data/repositories/QuranRepository";

export function useQuranData() {
  const [surahs, setSurahs] = useState<Surah[]>([]);
  const [ayahs, setAyahs] = useState<Ayah[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const repositoryRef = useRef(new QuranRepository());

  const loadSurahs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await repositoryRef.current.getSurahs();
      setSurahs(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load surahs");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadAyahs = useCallback(async (surahId: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await repositoryRef.current.getAyahs(surahId);
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
