import { View, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack } from "expo-router";
import { RecordButton } from "@src/components/audio/RecordButton";
import { ArabicText } from "@src/components/arabic/ArabicText";
import { LoadingSpinner } from "@src/components/common/LoadingSpinner";
import { ErrorDisplay } from "@src/components/common/ErrorDisplay";
import { useStreamingRecitation } from "@src/hooks/useStreamingRecitation";
import { useRecitationStore } from "@src/stores/recitationStore";

export default function RecitePracticeScreen() {
  const {
    state,
    selectedSurah,
    errorMessage,
    isStreaming,
    isConnecting,
    startRecitation,
    stopRecitation,
    reset,
  } = useStreamingRecitation();

  const selectedAyahNumber = useRecitationStore((s) => s.selectedAyahNumber);

  const handleRecordPress = () => {
    if (isStreaming || isConnecting) {
      stopRecitation();
    } else {
      startRecitation(selectedAyahNumber ?? undefined);
    }
  };

  const headerTitle = selectedSurah
    ? `${selectedSurah.nameSimple}${selectedAyahNumber ? ` - Ayah ${selectedAyahNumber}` : ""}`
    : "Practice";

  return (
    <SafeAreaView className="flex-1 bg-ivory dark:bg-d-bg" edges={["bottom"]}>
      <Stack.Screen options={{ title: headerTitle }} />

      <ScrollView className="flex-1" contentContainerClassName="pb-8">
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
