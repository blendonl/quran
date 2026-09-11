import { create } from "zustand";
import { TranscriptionSegment } from "../domain/models/TranscriptionSegment";
import { ElongationResult } from "../domain/models/ElongationResult";
import { RecitationResult } from "../domain/models/RecitationResult";
import { Surah } from "../domain/models/Surah";
import { Ayah } from "../domain/models/Ayah";

type RecitationState = "idle" | "recording" | "processing" | "completed" | "error";

interface RecitationStore {
  state: RecitationState;
  selectedSurah: Surah | null;
  selectedAyah: Ayah | null;
  segments: TranscriptionSegment[];
  transcribedText: string;
  elongationResult: ElongationResult | null;
  recitationResult: RecitationResult | null;
  errorMessage: string | null;

  setSelectedSurah: (surah: Surah | null) => void;
  setSelectedAyah: (ayah: Ayah | null) => void;
  startRecording: () => void;
  stopRecording: () => void;
  setProcessing: () => void;
  setTranscription: (text: string, segments: TranscriptionSegment[]) => void;
  setElongationResult: (result: ElongationResult) => void;
  setRecitationResult: (result: RecitationResult) => void;
  setError: (message: string) => void;
  reset: () => void;
}

const initialState = {
  state: "idle" as RecitationState,
  selectedSurah: null,
  selectedAyah: null,
  segments: [],
  transcribedText: "",
  elongationResult: null,
  recitationResult: null,
  errorMessage: null,
};

export const useRecitationStore = create<RecitationStore>((set) => ({
  ...initialState,

  setSelectedSurah: (surah) => set({ selectedSurah: surah }),
  setSelectedAyah: (ayah) => set({ selectedAyah: ayah }),

  startRecording: () =>
    set({
      state: "recording",
      segments: [],
      transcribedText: "",
      elongationResult: null,
      recitationResult: null,
      errorMessage: null,
    }),

  stopRecording: () => set({ state: "processing" }),
  setProcessing: () => set({ state: "processing" }),

  setTranscription: (text, segments) =>
    set({ transcribedText: text, segments }),

  setElongationResult: (result) => set({ elongationResult: result }),

  setRecitationResult: (result) =>
    set({ recitationResult: result, state: "completed" }),

  setError: (message) => set({ state: "error", errorMessage: message }),

  reset: () => set(initialState),
}));
