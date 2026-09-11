import { View, Text, ScrollView } from "react-native";
import { useEffect } from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack } from "expo-router";
import { RecordButton } from "@src/components/audio/RecordButton";
import { ArabicText } from "@src/components/arabic/ArabicText";
import { ElongatedTextDisplay } from "@src/components/arabic/ElongatedTextDisplay";
import { AyahComparison } from "@src/components/arabic/AyahComparison";
import { LoadingSpinner } from "@src/components/common/LoadingSpinner";
import { ProgressBar } from "@src/components/common/ProgressBar";
import { ErrorDisplay } from "@src/components/common/ErrorDisplay";
import { useRecitation } from "@src/hooks/useRecitation";
import { useSettingsStore } from "@src/stores/settingsStore";

export default function RecitePracticeScreen() {
  const {
    state,
    selectedSurah,
    selectedAyah,
    transcribedText,
    elongationResult,
    recitationResult,
    errorMessage,
    isWhisperReady,
    isWhisperLoading,
    whisperError,
    isRecording,
    initializeWhisper,
    startRecitation,
    stopRecitation,
    reset,
  } = useRecitation();

  const { modelDownloadProgress, modelStatus } = useSettingsStore();

  useEffect(() => {
    initializeWhisper();
  }, [initializeWhisper]);

  const handleRecordPress = async () => {
    if (isRecording) {
      await stopRecitation();
    } else {
      await startRecitation();
    }
  };

  const headerTitle = selectedSurah
    ? `${selectedSurah.nameSimple} - Ayah ${selectedAyah?.verseNumber ?? ""}`
    : "Practice";

  return (
    <SafeAreaView className="flex-1 bg-white" edges={["bottom"]}>
      <Stack.Screen options={{ title: headerTitle }} />

      <ScrollView className="flex-1" contentContainerClassName="pb-8">
        {selectedAyah && (
          <View className="mx-4 mt-4 rounded-xl bg-primary-50 p-4">
            <Text className="mb-2 text-xs font-medium uppercase text-primary-600">
              Reference ({selectedAyah.verseKey})
            </Text>
            <ArabicText text={selectedAyah.textUthmani} size="lg" />
          </View>
        )}

        {!isWhisperReady && !whisperError && (
          <View className="mx-4 mt-6">
            {modelStatus === "downloading" ? (
              <ProgressBar progress={modelDownloadProgress} label="Downloading speech model..." />
            ) : (
              <LoadingSpinner message="Initializing speech recognition..." />
            )}
          </View>
        )}

        {whisperError && (
          <View className="mx-4 mt-6">
            <ErrorDisplay message={whisperError} onRetry={initializeWhisper} />
          </View>
        )}

        <View className="items-center py-8">
          <RecordButton
            isRecording={isRecording}
            isProcessing={state === "processing"}
            isDisabled={!isWhisperReady || isWhisperLoading}
            onPress={handleRecordPress}
          />
        </View>

        {state === "processing" && (
          <View className="mx-4">
            <LoadingSpinner message="Processing your recitation..." />
          </View>
        )}

        {elongationResult && state !== "processing" && (
          <View className="mx-4 mb-4">
            <Text className="mb-2 text-sm font-medium text-gray-500">Your Recitation</Text>
            <View className="rounded-xl bg-gray-50 p-4">
              <ElongatedTextDisplay result={elongationResult} size="xl" />
            </View>
          </View>
        )}

        {recitationResult && state === "completed" && selectedAyah && (
          <View className="mx-4 mb-4">
            <Text className="mb-2 text-sm font-medium text-gray-500">Comparison</Text>
            <View className="rounded-xl bg-gray-50 p-4">
              <AyahComparison result={recitationResult} />
            </View>
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
