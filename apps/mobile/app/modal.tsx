import { StatusBar } from "expo-status-bar";
import { Platform, View, Text, ScrollView } from "react-native";

export default function ModalScreen() {
  return (
    <View className="flex-1 bg-white">
      <ScrollView className="flex-1 px-4 pt-6">
        <Text className="mb-4 text-2xl font-bold text-gray-900">About</Text>

        <Text className="mb-3 text-base leading-6 text-gray-700">
          Quran Recitation Practice is an AI-powered app that listens to your Quran recitation and
          provides real-time feedback.
        </Text>

        <Text className="mb-2 text-lg font-semibold text-gray-800">Features</Text>
        <Text className="mb-1 text-sm text-gray-600">
          - On-device speech recognition (no internet required after setup)
        </Text>
        <Text className="mb-1 text-sm text-gray-600">
          - Elongation detection (Madd) - see held sounds visually
        </Text>
        <Text className="mb-1 text-sm text-gray-600">
          - Word-by-word comparison with Quran text
        </Text>
        <Text className="mb-4 text-sm text-gray-600">
          - Accuracy scoring for each recitation
        </Text>

        <Text className="mb-2 text-lg font-semibold text-gray-800">Speech Model</Text>
        <Text className="mb-4 text-sm leading-5 text-gray-600">
          Uses tarteel-ai/whisper-base-ar-quran, a Whisper model fine-tuned on 25,000+ Quranic
          recitation clips from 1,200+ reciters, achieving 5.75% word error rate.
        </Text>
      </ScrollView>

      <StatusBar style={Platform.OS === "ios" ? "light" : "auto"} />
    </View>
  );
}
