import { create } from "zustand";
import { ElongationSettings } from "../domain/interfaces/IElongationDetector";
import { DEFAULT_ELONGATION_SETTINGS } from "../config/elongationConfig";
import { WhisperModelStatus } from "../domain/models/WhisperModel";

interface SettingsStore {
  elongationSettings: ElongationSettings;
  modelStatus: WhisperModelStatus;
  modelDownloadProgress: number;

  setElongationSettings: (settings: Partial<ElongationSettings>) => void;
  setModelStatus: (status: WhisperModelStatus) => void;
  setModelDownloadProgress: (progress: number) => void;
}

export const useSettingsStore = create<SettingsStore>((set) => ({
  elongationSettings: DEFAULT_ELONGATION_SETTINGS,
  modelStatus: "not_downloaded",
  modelDownloadProgress: 0,

  setElongationSettings: (settings) =>
    set((state) => ({
      elongationSettings: { ...state.elongationSettings, ...settings },
    })),

  setModelStatus: (status) => set({ modelStatus: status }),
  setModelDownloadProgress: (progress) => set({ modelDownloadProgress: progress }),
}));
