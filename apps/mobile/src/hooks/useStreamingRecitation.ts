import { useCallback, useEffect } from "react";
import { useRecitationStore } from "../stores/recitationStore";
import { SessionManager } from "../services/streaming/SessionManager";

export function useStreamingRecitation() {
  const state = useRecitationStore((s) => s.state);
  const connectionStatus = useRecitationStore((s) => s.connectionStatus);
  const selectedSurah = useRecitationStore((s) => s.selectedSurah);
  const errorMessage = useRecitationStore((s) => s.errorMessage);
  const surahCompleted = useRecitationStore((s) => s.surahCompleted);
  const nextSurahId = useRecitationStore((s) => s.nextSurahId);
  const reset = useRecitationStore((s) => s.reset);

  useEffect(() => {
    SessionManager.rebindCallbacks();
  }, []);

  const startRecitation = useCallback((ayahNumber?: number) => {
    const surah = useRecitationStore.getState().selectedSurah;
    if (surah && ayahNumber != null) {
      SessionManager.start({ surahId: surah.id, ayahNumber });
    } else {
      SessionManager.start();
    }
  }, []);

  const stopRecitation = useCallback(() => {
    SessionManager.stop();
  }, []);

  return {
    state,
    connectionStatus,
    selectedSurah,
    errorMessage,
    surahCompleted,
    nextSurahId,
    isStreaming: state === "streaming",
    isConnecting: state === "connecting",
    startRecitation,
    stopRecitation,
    reset,
  };
}
