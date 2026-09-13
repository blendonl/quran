import { useState, useCallback } from "react";
import { Translation } from "../domain/models/Translation";
import { quranRepository } from "../data/repositories/QuranRepository";

export function useTranslations() {
  const [translations, setTranslations] = useState<Translation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTranslations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await quranRepository.getTranslations();
      setTranslations(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load translations");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { translations, isLoading, error, loadTranslations };
}
