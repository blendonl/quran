import { useState, useCallback, useRef, useEffect } from "react";
import { WhisperService } from "../services/speech/WhisperService";
import { WhisperModelManager } from "../services/speech/WhisperModelManager";
import { TranscriptionResponse } from "../domain/interfaces/ISpeechRecognitionService";
import { useSettingsStore } from "../stores/settingsStore";

export function useWhisper() {
  const [isReady, setIsReady] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const serviceRef = useRef<WhisperService | null>(null);
  const modelManagerRef = useRef<WhisperModelManager>(new WhisperModelManager());

  const { setModelStatus, setModelDownloadProgress } = useSettingsStore();

  const initialize = useCallback(async () => {
    if (serviceRef.current?.isReady()) return;

    setIsLoading(true);
    setError(null);
    setModelStatus("downloading");

    try {
      const modelManager = modelManagerRef.current;
      const service = new WhisperService(modelManager);

      await modelManager.downloadModelWithFallback((progress) => {
        setModelDownloadProgress(progress);
      });

      setModelStatus("ready");
      await service.initialize();

      serviceRef.current = service;
      setIsReady(true);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Failed to initialize Whisper";
      setError(message);
      setModelStatus("error");
    } finally {
      setIsLoading(false);
    }
  }, [setModelStatus, setModelDownloadProgress]);

  const transcribe = useCallback(
    async (audioFilePath: string, prompt?: string): Promise<TranscriptionResponse | null> => {
      if (!serviceRef.current?.isReady()) {
        setError("Whisper not initialized");
        return null;
      }

      try {
        return await serviceRef.current.transcribe(audioFilePath, {
          language: "ar",
          prompt,
        });
      } catch (e) {
        const message = e instanceof Error ? e.message : "Transcription failed";
        setError(message);
        return null;
      }
    },
    [],
  );

  const release = useCallback(async () => {
    if (serviceRef.current) {
      await serviceRef.current.release();
      serviceRef.current = null;
      setIsReady(false);
    }
  }, []);

  useEffect(() => {
    return () => {
      serviceRef.current?.release();
    };
  }, []);

  return {
    isReady,
    isLoading,
    error,
    initialize,
    transcribe,
    release,
  };
}
