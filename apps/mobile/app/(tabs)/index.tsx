import { View, Text, ScrollView, Pressable } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { RecordButton } from "@src/components/audio/RecordButton";
import { LoadingSpinner } from "@src/components/common/LoadingSpinner";
import { ErrorDisplay } from "@src/components/common/ErrorDisplay";
import { useStreamingRecitation } from "@src/hooks/useStreamingRecitation";
import { useThemeColors } from "@src/config/themeColors";

export default function ReciteScreen() {
  const {
    state,
    errorMessage,
    isStreaming,
    isConnecting,
    startRecitation,
    stopRecitation,
    reset,
  } = useStreamingRecitation();
  const router = useRouter();
  const colors = useThemeColors();

  const handleRecordPress = () => {
    if (isStreaming || isConnecting) {
      stopRecitation();
    } else {
      startRecitation();
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-ivory dark:bg-d-bg" edges={["bottom"]}>
      <ScrollView className="flex-1" contentContainerClassName="pb-8">
        <View className="flex-row items-center justify-between px-4 pt-6">
          <View className="flex-1">
            <Text className="mb-1 text-2xl font-bold text-ink dark:text-d-ink">Quran Recitation</Text>
            <Text className="mb-6 text-sm text-ink-muted dark:text-d-ink-muted">
              Practice your recitation with AI feedback
            </Text>
          </View>
          <Pressable onPress={() => router.push("/settings")} accessibilityLabel="Settings">
            <Ionicons name="settings-outline" size={24} color={colors.ink.muted} />
          </Pressable>
        </View>

        <View className="items-center py-8">
          <RecordButton
            isRecording={isStreaming}
            isProcessing={isConnecting}
            isDisabled={false}
            onPress={handleRecordPress}
          />
        </View>

        {isConnecting && (
          <View className="mx-4">
            <LoadingSpinner message="Connecting to server..." />
          </View>
        )}

        {errorMessage && (
          <View className="mx-4">
            <ErrorDisplay message={errorMessage} onRetry={reset} />
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
