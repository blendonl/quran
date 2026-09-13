export type AudioEncoding = "pcm_s16le" | "opus";
export type GainMode = "near" | "far";

export const STREAMING_CONFIG = {
  wsUrl: process.env.EXPO_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/recite",
  sampleRate: 16000,
  channels: 1 as const,
  bitsPerSample: 16,
  encoding: (process.env.EXPO_PUBLIC_AUDIO_ENCODING ?? "pcm_s16le") as AudioEncoding,
  opus: {
    bitrate: 24000,
    frameDurationMs: 20,
  },
  gain: {
    near: { targetRms: 3000, maxGain: 10 },
    far: { targetRms: 5000, maxGain: 30, noiseGateRms: 150 },
  },
} as const;
