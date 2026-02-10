export interface AudioCaptureConfig {
  sampleRate: number;
  channels: number;
  bitDepth: number;
}

export interface IAudioCaptureService {
  requestPermissions(): Promise<boolean>;
  startRecording(): Promise<void>;
  stopRecording(): Promise<string>;
  isRecording(): boolean;
}
