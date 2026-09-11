import { useCallback, useEffect, useRef, useState } from "react";
import { useRecitationStore } from "../stores/recitationStore";
import { SessionManager } from "../services/streaming/SessionManager";

export function useFreeRecitation(onFound: () => void) {
  const onFoundRef = useRef(onFound);
  onFoundRef.current = onFound;

  const connectionStatus = useRecitationStore((s) => s.connectionStatus);
  const state = useRecitationStore((s) => s.state);
  const [isListening, setIsListening] = useState(false);
  const foundRef = useRef(false);

  useEffect(() => {
    if (!isListening) return;

    const unsubscribe = useRecitationStore.subscribe((s) => {
      if (
        !foundRef.current &&
        s.currentSurahId != null &&
        s.currentAyahNumber != null
      ) {
        foundRef.current = true;
        setIsListening(false);
        onFoundRef.current();
      }
    });

    return unsubscribe;
  }, [isListening]);

  const startListening = useCallback(() => {
    foundRef.current = false;
    setIsListening(true);
    SessionManager.start();
  }, []);

  const stopListening = useCallback(() => {
    setIsListening(false);
    SessionManager.stop();
  }, []);

  return {
    isListening,
    connectionStatus,
    isConnecting: state === "connecting",
    startListening,
    stopListening,
  };
}
