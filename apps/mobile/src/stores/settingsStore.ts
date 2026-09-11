import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { STREAMING_CONFIG, type GainMode } from "../config/streamingConfig";
import { DEFAULT_TRANSLATION_ID } from "../config/apiConfig";

const DEFAULT_FONT_SIZE = 22;
const MIN_FONT_SIZE = 16;
const MAX_FONT_SIZE = 36;

const STORAGE_KEY = "settings-storage";

export type ColorScheme = "light" | "dark" | "system";

interface SettingsState {
  serverUrl: string;
  fontSize: number;
  translationId: number;
  showTranslation: boolean;
  colorScheme: ColorScheme;
  gainMode: GainMode;
}

interface SettingsStore extends SettingsState {
  setServerUrl: (url: string) => void;
  setFontSize: (size: number) => void;
  setTranslationId: (id: number) => void;
  setShowTranslation: (show: boolean) => void;
  setColorScheme: (scheme: ColorScheme) => void;
  setGainMode: (mode: GainMode) => void;
}

const defaults: SettingsState = {
  serverUrl: STREAMING_CONFIG.wsUrl,
  fontSize: DEFAULT_FONT_SIZE,
  translationId: DEFAULT_TRANSLATION_ID,
  showTranslation: true,
  colorScheme: "system",
  gainMode: "near",
};

function persistState(state: SettingsStore) {
  const { serverUrl, fontSize, translationId, showTranslation, colorScheme, gainMode } = state;
  AsyncStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ serverUrl, fontSize, translationId, showTranslation, colorScheme, gainMode }),
  ).catch(() => {});
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  ...defaults,
  setServerUrl: (url) => {
    set({ serverUrl: url });
    persistState(get());
  },
  setFontSize: (size) => {
    set({ fontSize: Math.round(Math.min(MAX_FONT_SIZE, Math.max(MIN_FONT_SIZE, size))) });
    persistState(get());
  },
  setTranslationId: (id) => {
    set({ translationId: id });
    persistState(get());
  },
  setShowTranslation: (show) => {
    set({ showTranslation: show });
    persistState(get());
  },
  setColorScheme: (scheme) => {
    set({ colorScheme: scheme });
    persistState(get());
  },
  setGainMode: (mode) => {
    set({ gainMode: mode });
    persistState(get());
  },
}));

AsyncStorage.getItem(STORAGE_KEY)
  .then((raw) => {
    if (!raw) return;
    const saved = JSON.parse(raw) as Partial<SettingsState>;
    useSettingsStore.setState({ ...defaults, ...saved });
  })
  .catch(() => {});

export { MIN_FONT_SIZE, MAX_FONT_SIZE };
