import { create } from "zustand";
import { Surah } from "../domain/models/Surah";
import { PositionUpdate } from "../domain/models/PositionUpdate";
import {
  LetterStatusValue,
  LetterStatusUpdate,
} from "../domain/models/LetterStatus";
import {
  TajweedGrade,
  TajweedRule,
  TajweedGradeUpdate,
} from "../domain/models/TajweedStatus";
import {
  RecitationErrorDetail,
  RecitationErrorUpdate,
} from "../domain/models/RecitationError";
import {
  WordStatusValue,
  WordStatusUpdate,
} from "../domain/models/WordStatus";

type RecitationState = "idle" | "connecting" | "streaming" | "error";
type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

type LetterStatusMap = Record<
  number,
  Record<number, Record<number, LetterStatusValue>>
>;

interface TajweedEntry {
  rule: TajweedRule;
  grade: TajweedGrade;
}

type TajweedStatusMap = Record<
  number,
  Record<number, Record<number, TajweedEntry>>
>;

interface WordStatusEntry {
  status: WordStatusValue;
  confidence: number;
  tajweedGrade: string | null;
}

type WordStatusMap = Record<number, Record<number, WordStatusEntry>>;

interface RecitationStore {
  state: RecitationState;
  connectionStatus: ConnectionStatus;
  selectedSurah: Surah | null;
  selectedAyahNumber: number | null;
  currentSurahId: number | null;
  currentAyahNumber: number | null;
  currentWordIndex: number | null;
  confidence: number;
  errorMessage: string | null;
  letterStatuses: LetterStatusMap;
  tajweedStatuses: TajweedStatusMap;
  recitationErrors: Record<number, RecitationErrorDetail[]>;
  wordStatuses: WordStatusMap;
  completedAyahs: Record<number, true>;
  surahCompleted: boolean;
  nextSurahId: number | null;
  recitationMode: "following" | "learning";

  selectAyah: (ayahNumber: number | null) => void;
  setRecitationMode: (mode: "following" | "learning") => void;
  updatePosition: (update: PositionUpdate) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  startStreaming: () => void;
  stopStreaming: () => void;
  setError: (message: string) => void;
  reset: () => void;
  setSelectedSurah: (surah: Surah | null) => void;
  applyLetterStatuses: (update: LetterStatusUpdate) => void;
  applyTajweedStatuses: (update: TajweedGradeUpdate) => void;
  applyRecitationErrors: (update: RecitationErrorUpdate) => void;
  applyWordStatuses: (update: WordStatusUpdate) => void;
  clearLetterStatusesForAyah: (ayahNumber: number) => void;
  markAyahCompleted: (ayahNumber: number) => void;
  setSurahCompleted: (nextSurahId: number | null) => void;
}

const initialState = {
  state: "idle" as RecitationState,
  connectionStatus: "disconnected" as ConnectionStatus,
  selectedSurah: null as Surah | null,
  selectedAyahNumber: null as number | null,
  currentSurahId: null as number | null,
  currentAyahNumber: null as number | null,
  currentWordIndex: null as number | null,
  confidence: 0,
  errorMessage: null as string | null,
  letterStatuses: {} as LetterStatusMap,
  tajweedStatuses: {} as TajweedStatusMap,
  recitationErrors: {} as Record<number, RecitationErrorDetail[]>,
  wordStatuses: {} as WordStatusMap,
  completedAyahs: {} as Record<number, true>,
  surahCompleted: false,
  nextSurahId: null as number | null,
  recitationMode: "following" as "following" | "learning",
};

export const useRecitationStore = create<RecitationStore>((set) => ({
  ...initialState,

  selectAyah: (ayahNumber) => set({ selectedAyahNumber: ayahNumber }),

  updatePosition: (update) =>
    set({
      currentSurahId: update.surahId,
      currentAyahNumber: update.ayahNumber,
      currentWordIndex: update.wordIndex,
      confidence: update.confidence,
    }),

  setConnectionStatus: (status) =>
    set({
      connectionStatus: status,
      state: status === "connected" ? "streaming" : status === "connecting" ? "connecting" : "idle",
    }),

  startStreaming: () =>
    set({
      state: "connecting",
      connectionStatus: "connecting",
      selectedAyahNumber: null,
      currentSurahId: null,
      currentAyahNumber: null,
      currentWordIndex: null,
      confidence: 0,
      errorMessage: null,
      letterStatuses: {},
      tajweedStatuses: {},
      recitationErrors: {},
      wordStatuses: {},
      completedAyahs: {},
      surahCompleted: false,
      nextSurahId: null,
      recitationMode: "following",
    }),

  stopStreaming: () =>
    set({
      state: "idle",
      connectionStatus: "disconnected",
    }),

  setError: (message) =>
    set({
      state: "error",
      connectionStatus: "error",
      errorMessage: message,
    }),

  reset: () => set(initialState),

  setRecitationMode: (mode) => set({ recitationMode: mode }),

  setSelectedSurah: (surah) => set({ selectedSurah: surah }),

  applyLetterStatuses: (update) => {
    set((state) => {
      const newStatuses = { ...state.letterStatuses };
      const ayahMap = { ...newStatuses[update.ayahNumber] };
      for (const u of update.updates) {
        const wordMap = { ...ayahMap[u.wordIndex] };
        wordMap[u.letterIndex] = u.status;
        ayahMap[u.wordIndex] = wordMap;
      }
      newStatuses[update.ayahNumber] = ayahMap;
      return { letterStatuses: newStatuses };
    });
  },

  applyTajweedStatuses: (update) => {
    set((state) => {
      const newStatuses = { ...state.tajweedStatuses };
      const ayahMap = { ...newStatuses[update.ayahNumber] };
      for (const u of update.updates) {
        const wordMap = { ...ayahMap[u.wordIndex] };
        wordMap[u.letterIndex] = { rule: u.rule, grade: u.grade };
        ayahMap[u.wordIndex] = wordMap;
      }
      newStatuses[update.ayahNumber] = ayahMap;
      return { tajweedStatuses: newStatuses };
    });
  },

  applyRecitationErrors: (update) =>
    set((state) => {
      const newErrors = { ...state.recitationErrors };
      const existing = newErrors[update.ayahNumber] ?? [];
      const seen = new Set(
        existing.map((e) => `${e.uthmaniStart}:${e.uthmaniEnd}:${e.expectedPhoneme}`),
      );
      const merged = [...existing];
      for (const e of update.errors) {
        const key = `${e.uthmaniStart}:${e.uthmaniEnd}:${e.expectedPhoneme}`;
        if (!seen.has(key)) {
          seen.add(key);
          merged.push(e);
        }
      }
      newErrors[update.ayahNumber] = merged;
      return { recitationErrors: newErrors };
    }),

  applyWordStatuses: (update) =>
    set((state) => {
      const newStatuses = { ...state.wordStatuses };
      const ayahMap = { ...newStatuses[update.ayahNumber] };
      for (const u of update.updates) {
        ayahMap[u.wordIndex] = {
          status: u.status,
          confidence: u.confidence,
          tajweedGrade: u.tajweedGrade,
        };
      }
      newStatuses[update.ayahNumber] = ayahMap;
      return { wordStatuses: newStatuses };
    }),

  clearLetterStatusesForAyah: (ayahNumber) =>
    set((state) => {
      const newStatuses = { ...state.letterStatuses };
      delete newStatuses[ayahNumber];
      const newTajweed = { ...state.tajweedStatuses };
      delete newTajweed[ayahNumber];
      const newErrors = { ...state.recitationErrors };
      delete newErrors[ayahNumber];
      const newWordStatuses = { ...state.wordStatuses };
      delete newWordStatuses[ayahNumber];
      return { letterStatuses: newStatuses, tajweedStatuses: newTajweed, recitationErrors: newErrors, wordStatuses: newWordStatuses };
    }),

  markAyahCompleted: (ayahNumber) =>
    set((state) => ({
      completedAyahs: { ...state.completedAyahs, [ayahNumber]: true as const },
    })),

  setSurahCompleted: (nextSurahId) =>
    set({ surahCompleted: true, nextSurahId }),
}));
