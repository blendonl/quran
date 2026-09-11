import { useCallback, useRef } from "react";
import { useWhisper } from "./useWhisper";
import { useAudioCapture } from "./useAudioCapture";
import { useRecitationStore } from "../stores/recitationStore";
import { useSettingsStore } from "../stores/settingsStore";
import { ElongationDetector } from "../services/elongation/ElongationDetector";
import { RecitationComparator } from "../services/comparison/RecitationComparator";

export function useRecitation() {
  const whisper = useWhisper();
  const audio = useAudioCapture();
  const store = useRecitationStore();
  const { elongationSettings } = useSettingsStore();

  const elongationDetectorRef = useRef(new ElongationDetector());
  const comparatorRef = useRef(new RecitationComparator());

  const startRecitation = useCallback(async () => {
    if (!whisper.isReady) {
      store.setError("Speech recognition not ready. Please wait for model to load.");
      return;
    }

    store.startRecording();
    await audio.startRecording();
  }, [whisper.isReady, store, audio]);

  const stopRecitation = useCallback(async () => {
    store.stopRecording();

    const audioUri = await audio.stopRecording();
    if (!audioUri) {
      store.setError("Failed to capture audio");
      return;
    }

    store.setProcessing();

    const ayahText = store.selectedAyah?.textUthmani;
    const result = await whisper.transcribe(audioUri, ayahText);

    if (!result) {
      store.setError("Transcription failed");
      return;
    }

    store.setTranscription(result.text, result.segments);

    const elongationResult = elongationDetectorRef.current.detect(
      result.segments,
      elongationSettings,
    );
    store.setElongationResult(elongationResult);

    if (store.selectedAyah) {
      const comparisonResult = comparatorRef.current.compare(
        result.text,
        store.selectedAyah.textUthmani,
      );
      store.setRecitationResult(comparisonResult);
    } else {
      store.setRecitationResult({
        recitedText: result.text,
        expectedText: "",
        wordMatches: [],
        accuracy: 0,
      });
    }
  }, [audio, whisper, store, elongationSettings]);

  return {
    isWhisperReady: whisper.isReady,
    isWhisperLoading: whisper.isLoading,
    whisperError: whisper.error,
    initializeWhisper: whisper.initialize,
    startRecitation,
    stopRecitation,
    isRecording: audio.isRecording,
    ...store,
  };
}
