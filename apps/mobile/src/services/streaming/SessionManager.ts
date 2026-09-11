import { Platform, PermissionsAndroid } from "react-native";
import { ExpoAudioStreamModule } from "@siteed/expo-audio-studio";
import { LegacyEventEmitter } from "expo-modules-core";
import { WebSocketClient } from "./WebSocketClient";
import { recitationUpdateFilter } from "./RecitationUpdateFilter";
import { useRecitationStore } from "../../stores/recitationStore";
import { STREAMING_CONFIG } from "../../config/streamingConfig";
import { useSettingsStore } from "../../stores/settingsStore";

const audioEmitter = new LegacyEventEmitter(ExpoAudioStreamModule);

export interface StartPosition {
  surahId: number;
  ayahNumber: number;
}

let client: WebSocketClient | null = null;
let audioActive = false;
let pendingStartPosition: StartPosition | null = null;
let audioSubscription: { remove(): void } | null = null;

function getServerUrl() {
  return useSettingsStore.getState().serverUrl;
}

function getGainParams() {
  const mode = useSettingsStore.getState().gainMode;
  return STREAMING_CONFIG.gain[mode];
}

function normalizeGain(pcm: Int16Array): Int16Array {
  if (pcm.length === 0) return pcm;

  const params = getGainParams();

  let sumSquares = 0;
  for (let i = 0; i < pcm.length; i++) {
    sumSquares += pcm[i] * pcm[i];
  }
  const rms = Math.sqrt(sumSquares / pcm.length);

  if ("noiseGateRms" in params && rms < params.noiseGateRms) {
    return new Int16Array(pcm.length);
  }

  if (rms < 1) return pcm;

  const gain = Math.min(params.targetRms / rms, params.maxGain);
  if (Math.abs(gain - 1.0) < 0.05) return pcm;

  const result = new Int16Array(pcm.length);
  for (let i = 0; i < pcm.length; i++) {
    result[i] = Math.max(-32768, Math.min(32767, Math.round(pcm[i] * gain)));
  }
  return result;
}

function getEffectiveEncoding() {
  if (Platform.OS === "ios" && STREAMING_CONFIG.encoding === "opus") {
    return "pcm_s16le";
  }
  return STREAMING_CONFIG.encoding;
}

function bindStoreCallbacks() {
  if (!client) return;

  recitationUpdateFilter.bind(client, () => useRecitationStore.getState());

  client.onConnectionChange = (status) => {
    useRecitationStore.getState().setConnectionStatus(status);
    if (status === "connected" && client) {
      const encoding = getEffectiveEncoding();
      const controlMsg: Record<string, unknown> = {
        type: "session.start",
        sample_rate: STREAMING_CONFIG.sampleRate,
        encoding,
      };
      if (pendingStartPosition) {
        controlMsg.surah_id = pendingStartPosition.surahId;
        controlMsg.ayah_number = pendingStartPosition.ayahNumber;
        pendingStartPosition = null;
      }
      client.sendControl(controlMsg);
    }
  };

  client.onError = useRecitationStore.getState().setError;

  client.onSurahCompleted = (surahId, nextSurahId) => {
    useRecitationStore.getState().setSurahCompleted(nextSurahId);
    stopAudio();
    if (client) {
      client.sendControl({ type: "session.stop" });
      client.disconnect();
      client = null;
    }
    useRecitationStore.getState().stopStreaming();
  };

  client.onSessionReady = () => {
    startAudio();
  };
}

async function requestMicPermission(): Promise<boolean> {
  if (Platform.OS !== "android") return true;
  const granted = await PermissionsAndroid.request(
    PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
  );
  return granted === PermissionsAndroid.RESULTS.GRANTED;
}

async function startAudio() {
  if (audioActive) return;

  const hasPermission = await requestMicPermission();
  if (!hasPermission) {
    useRecitationStore.getState().setError("Microphone permission denied");
    return;
  }

  audioSubscription = audioEmitter.addListener("AudioData", (event: {
    encoded?: string;
  }) => {
    if (!audioActive || !client) return;

    if (event.encoded) {
      const binaryStr = atob(event.encoded);
      const raw = new Uint8Array(binaryStr.length);
      for (let i = 0; i < binaryStr.length; i++) {
        raw[i] = binaryStr.charCodeAt(i);
      }
      const pcm = new Int16Array(raw.buffer, raw.byteOffset, raw.byteLength / 2);
      const normalized = normalizeGain(pcm);
      client.sendAudioChunk(normalized.buffer as ArrayBuffer);
    }
  });

  const recordingConfig: Record<string, unknown> = {
    sampleRate: STREAMING_CONFIG.sampleRate,
    channels: STREAMING_CONFIG.channels,
    bitDepth: STREAMING_CONFIG.bitsPerSample,
  };

  audioActive = true;
  await ExpoAudioStreamModule.startRecording(recordingConfig);
}

async function stopAudio() {
  if (!audioActive) return;
  audioActive = false;
  if (audioSubscription) {
    audioSubscription.remove();
    audioSubscription = null;
  }
  await ExpoAudioStreamModule.stopRecording();
}

export const SessionManager = {
  start(startPosition?: StartPosition) {
    if (client) {
      stopAudio();
      client.disconnect();
      client = null;
    }
    recitationUpdateFilter.reset();
    pendingStartPosition = startPosition ?? null;
    const url = getServerUrl();
    console.log(`[Session] Starting session, server URL: ${url}`);
    useRecitationStore.getState().startStreaming();
    client = new WebSocketClient();
    bindStoreCallbacks();
    client.connect(url);
  },

  stop() {
    stopAudio();
    if (client) {
      client.sendControl({ type: "session.stop" });
      client.disconnect();
      client = null;
    }
    useRecitationStore.getState().stopStreaming();
  },

  rebindCallbacks() {
    bindStoreCallbacks();
  },

  get isActive() {
    const { state } = useRecitationStore.getState();
    return state === "streaming" || state === "connecting";
  },
};
