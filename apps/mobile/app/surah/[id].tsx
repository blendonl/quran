import { useEffect, useCallback } from "react";
import { View, Text, Pressable } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useThemeColors } from "@src/config/themeColors";
import { ErrorDisplay } from "@src/components/common/ErrorDisplay";
import { QuranPageView } from "@src/components/quran/QuranPageView";
import { ReciteActionBar } from "@src/components/recite/ReciteActionBar";
import { SurahCompletedOverlay } from "@src/components/recite/SurahCompletedOverlay";
import { useStreamingRecitation } from "@src/hooks/useStreamingRecitation";
import { useQuranData } from "@src/hooks/useQuranData";
import { useRecitationStore } from "@src/stores/recitationStore";
import { useSettingsStore } from "@src/stores/settingsStore";

export default function SurahReadingScreen() {
  const { id, ayah } = useLocalSearchParams<{ id: string; ayah?: string }>();
  const surahId = Number(id);
  const initialAyah = ayah ? Number(ayah) : undefined;
  const router = useRouter();
  const colors = useThemeColors();

  const {
    state,
    connectionStatus,
    selectedSurah,
    errorMessage,
    isStreaming,
    isConnecting,
    surahCompleted,
    nextSurahId,
    startRecitation,
    stopRecitation,
    reset,
  } = useStreamingRecitation();

  const selectedAyahNumber = useRecitationStore((s) => s.selectedAyahNumber);
  const selectAyah = useRecitationStore((s) => s.selectAyah);
  const recitationMode = useRecitationStore((s) => s.recitationMode);
  const setRecitationMode = useRecitationStore((s) => s.setRecitationMode);

  const translationId = useSettingsStore((s) => s.translationId);
  const showTranslation = useSettingsStore((s) => s.showTranslation);

  const { ayahs, isLoading, error, loadAyahs } = useQuranData();

  // Clear stale free-recitation position so it doesn't auto-scroll the list
  useEffect(() => {
    if (initialAyah != null) {
      useRecitationStore.setState({ currentAyahNumber: null, currentSurahId: null });
    }
  }, [initialAyah]);

  useEffect(() => {
    if (surahId) {
      loadAyahs(surahId, showTranslation ? translationId : undefined);
    }
  }, [surahId, translationId, showTranslation, loadAyahs]);

  const handleAyahPress = useCallback(
    (verseNumber: number) => {
      if (isStreaming || isConnecting) return;
      selectAyah(selectedAyahNumber === verseNumber ? null : verseNumber);
    },
    [isStreaming, isConnecting, selectedAyahNumber, selectAyah],
  );

  const handleStart = useCallback(() => {
    if (selectedAyahNumber != null) {
      startRecitation(selectedAyahNumber);
    }
  }, [selectedAyahNumber, startRecitation]);

  const handleToggleMode = useCallback(() => {
    setRecitationMode(recitationMode === "following" ? "learning" : "following");
  }, [recitationMode, setRecitationMode]);

  useEffect(() => {
    const store = useRecitationStore.getState();
    if (store.surahCompleted) {
      store.reset();
    }
  }, [surahId]);

  const handleDismiss = useCallback(() => {
    useRecitationStore.getState().reset();
  }, []);

  const handleContinueToNext = useCallback(() => {
    if (nextSurahId == null) return;
    stopRecitation();
    useRecitationStore.getState().reset();
    router.replace(`/surah/${nextSurahId}`);
  }, [nextSurahId, stopRecitation, router]);

  const handleDone = useCallback(() => {
    stopRecitation();
    useRecitationStore.getState().reset();
    router.back();
  }, [stopRecitation, router]);

  const revelationLabel =
    selectedSurah?.revelationPlace === "makkah" ? "Meccan" : "Medinan";

  return (
    <SafeAreaView className="flex-1 bg-ivory dark:bg-d-bg">
      <View className="items-center border-b border-gold-100 px-4 pb-3 pt-1 dark:border-gold-800">
        <View className="w-full flex-row items-center justify-between">
          <Pressable
            className="h-11 w-11 items-center justify-center rounded-full bg-primary-50 dark:bg-primary-950"
            onPress={() => router.back()}
            accessibilityRole="button"
            accessibilityLabel="Go back"
          >
            <Ionicons name="arrow-back" size={20} color={colors.primary[500]} />
          </Pressable>
          <View className="w-11" />
        </View>
        <Text className="mt-1 text-xl text-gold-500 dark:text-gold-300">
          {selectedSurah?.nameArabic}
        </Text>
        <Text className="mt-0.5 text-base font-semibold text-primary-500 dark:text-primary-300">
          {selectedSurah?.nameSimple}
        </Text>
        {selectedSurah && (
          <Text className="mt-1 text-xs text-gold-600 dark:text-gold-400">
            {revelationLabel} · {selectedSurah.versesCount} verses · {selectedSurah.translatedName.name}
          </Text>
        )}
      </View>

      {error ? (
        <ErrorDisplay message={error} onRetry={() => loadAyahs(surahId)} />
      ) : (
        <QuranPageView
          ayahs={ayahs}
          isLoading={isLoading}
          bismillahPre={selectedSurah?.bismillahPre ?? false}
          onAyahPress={handleAyahPress}
          initialScrollToAyah={initialAyah}
        />
      )}

      {errorMessage && (
        <View className="absolute bottom-24 left-4 right-4">
          <ErrorDisplay message={errorMessage} onRetry={reset} />
        </View>
      )}

      {!surahCompleted && (
        <ReciteActionBar
          selectedAyahNumber={selectedAyahNumber}
          isStreaming={isStreaming}
          isConnecting={isConnecting}
          isDisabled={state === "error"}
          connectionStatus={connectionStatus}
          recitationMode={recitationMode}
          onStart={handleStart}
          onStop={stopRecitation}
          onToggleMode={handleToggleMode}
        />
      )}

      <SurahCompletedOverlay
        visible={surahCompleted}
        nextSurahId={nextSurahId}
        onContinue={handleContinueToNext}
        onDone={handleDone}
        onDismiss={handleDismiss}
      />
    </SafeAreaView>
  );
}
