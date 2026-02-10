import {
  requestRecordingPermissionsAsync,
  getRecordingPermissionsAsync,
} from "expo-audio";
import { IAudioCaptureService } from "../../domain/interfaces/IAudioCaptureService";
import { PermissionError } from "../../domain/errors/PermissionError";
import { AudioCaptureError } from "../../domain/errors/AudioCaptureError";

export class AudioCaptureService implements IAudioCaptureService {
  async requestPermissions(): Promise<boolean> {
    try {
      const permissions = await getRecordingPermissionsAsync();
      if (permissions.granted) return true;

      if (!permissions.canAskAgain) {
        throw new PermissionError(
          "Microphone permission denied. Please enable it in Settings.",
        );
      }

      const result = await requestRecordingPermissionsAsync();
      return result.granted;
    } catch (error) {
      if (error instanceof PermissionError) throw error;
      throw new AudioCaptureError(`Failed to request permissions: ${error}`);
    }
  }

  async startRecording(): Promise<void> {
    throw new AudioCaptureError(
      "Use useAudioCapture hook for recording. This service only handles permissions.",
    );
  }

  async stopRecording(): Promise<string> {
    throw new AudioCaptureError(
      "Use useAudioCapture hook for recording. This service only handles permissions.",
    );
  }

  isRecording(): boolean {
    return false;
  }
}
