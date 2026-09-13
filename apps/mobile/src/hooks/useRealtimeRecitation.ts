import { useState, useCallback, useRef, useEffect } from "react";
import { initWhisper, WhisperContext, TranscribeRealtimeEvent } from "whisper.rn";
import { useRecitationStore } from "../stores/recitationStore";
import { useSettingsStore } from "../stores/settingsStore";
import { ElongationDetector } from "../services/elongation/ElongationDetector";
import { RecitationComparator } from "../services/comparison/RecitationComparator";
import { TranscriptionSegment } from "../domain/models/TranscriptionSegment";
import { WhisperModelManager } from "../services/speech/WhisperModelManager";
import { WHISPER_TRANSCRIPTION_OPTIONS } from "../config/whisperConfig";

interface RealtimeHandle {
  stop: () => Promise<void>;
  subscribe: (callback: (event: TranscribeRealtimeEvent) => void) => void;
}

export function useRealtimeRecitation() {
  const [isReady, setIsReady] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const contextRef = useRef<WhisperContext | null>(null);
  const realtimeRef = useRef<RealtimeHandle | null>(null);
  const modelManagerRef = useRef(new WhisperModelManager());
  const elongationDetectorRef = useRef(new ElongationDetector());
  const comparatorRef = useRef(new RecitationComparator());

  const store = useRecitationStore();
  const { elongationSettings, setModelStatus, setModelDownloadProgress } = useSettingsStore();

  const initialize = useCallback(async () => {
    if (contextRef.current) return;
    setIsLoading(true);
    setError(null);
    setModelStatus("downloading");

    try {
      const modelPath = await modelManagerRef.current.downloadModelWithFallback((progress) => {
        setModelDownloadProgress(progress);
      });
      setModelStatus("ready");

      contextRef.current = await initWhisper({ filePath: modelPath });
      setIsReady(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to initialize");
      setModelStatus("error");
    } finally {
      setIsLoading(false);
    }
  }, [setModelStatus, setModelDownloadProgress]);

  const startListening = useCallback(async () => {
    if (!contextRef.current) {
      setError("Not initialized");
      return;
    }

    store.startRecording();
    setError(null);

    try {
      const ayahText = store.selectedAyah?.textUthmani;
      const realtime = await contextRef.current.transcribeRealtime({
        ...WHISPER_TRANSCRIPTION_OPTIONS,
        realtimeAudioSec: 30,
        realtimeAudioSliceSec: 5,
        realtimeAudioMinSec: 1,
        prompt: ayahText,
      });

      realtimeRef.current = realtime;
      setIsListening(true);

      realtime.subscribe((event) => {
        if (event.code !== 0) return;

        const allSegments: TranscriptionSegment[] = [];
        let fullText = "";

        if (event.slices) {
          for (const slice of event.slices) {
            if (slice.data) {
              fullText += slice.data.result;
              for (const seg of slice.data.segments) {
                allSegments.push({
                  text: seg.text.trim(),
                  t0: seg.t0,
                  t1: seg.t1,
                  confidence: 1.0,
                });
              }
            }
          }
        } else if (event.data) {
          fullText = event.data.result;
          for (const seg of event.data.segments) {
            allSegments.push({
              text: seg.text.trim(),
              t0: seg.t0,
              t1: seg.t1,
              confidence: 1.0,
            });
          }
        }

        if (fullText.trim().length > 0) {
          store.setTranscription(fullText, allSegments);

          const elongationResult = elongationDetectorRef.current.detect(
            allSegments,
            elongationSettings,
          );
          store.setElongationResult(elongationResult);
        }

        if (!event.isCapturing) {
          setIsListening(false);
          if (store.selectedAyah && fullText.trim().length > 0) {
            const comparison = comparatorRef.current.compare(
              fullText,
              store.selectedAyah.textUthmani,
            );
            store.setRecitationResult(comparison);
          }
        }
      });
    } catch (e) {
      setIsListening(false);
      store.setError(e instanceof Error ? e.message : "Failed to start listening");
    }
  }, [store, elongationSettings]);

  const stopListening = useCallback(async () => {
    if (realtimeRef.current) {
      await realtimeRef.current.stop();
      realtimeRef.current = null;
    }
    setIsListening(false);
  }, []);

  useEffect(() => {
    return () => {
      realtimeRef.current?.stop();
      contextRef.current?.release();
    };
  }, []);

  return {
    isReady,
    isListening,
    isLoading,
    error,
    initialize,
    startListening,
    stopListening,
  };
}
