import { useState, useCallback } from "react";
import {
  useAudioRecorder,
  requestRecordingPermissionsAsync,
  getRecordingPermissionsAsync,
  IOSOutputFormat,
  AudioQuality,
} from "expo-audio";
import type { RecordingOptions } from "expo-audio";

const WHISPER_RECORDING_OPTIONS: RecordingOptions = {
  extension: ".wav",
  sampleRate: 16000,
  numberOfChannels: 1,
  bitRate: 256000,
  android: {
    outputFormat: "default",
    audioEncoder: "default",
    sampleRate: 16000,
  },
  ios: {
    outputFormat: IOSOutputFormat.LINEARPCM,
    audioQuality: AudioQuality.MAX,
    sampleRate: 16000,
    linearPCMBitDepth: 16,
    linearPCMIsBigEndian: false,
    linearPCMIsFloat: false,
  },
  web: {
    mimeType: "audio/wav",
    bitsPerSecond: 256000,
  },
};

export function useAudioCapture() {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recorder = useAudioRecorder(WHISPER_RECORDING_OPTIONS);

  const requestPermissions = useCallback(async (): Promise<boolean> => {
    try {
      const permissions = await getRecordingPermissionsAsync();
      if (permissions.granted) return true;

      if (!permissions.canAskAgain) {
        setError("Microphone permission denied. Please enable it in Settings.");
        return false;
      }

      const result = await requestRecordingPermissionsAsync();
      return result.granted;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to request permissions");
      return false;
    }
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const hasPermission = await requestPermissions();
      if (!hasPermission) {
        setError("Microphone permission not granted");
        return;
      }

      recorder.record();
      setIsRecording(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start recording");
    }
  }, [recorder, requestPermissions]);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    try {
      await recorder.stop();
      setIsRecording(false);
      return recorder.uri;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to stop recording");
      setIsRecording(false);
      return null;
    }
  }, [recorder]);

  return {
    isRecording,
    error,
    startRecording,
    stopRecording,
    requestPermissions,
  };
}
