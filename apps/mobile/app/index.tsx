import { useEffect, useCallback, useState } from "react";
import { View, Text, Pressable } from "react-native";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useThemeColors } from "@src/config/themeColors";
import { SurahList } from "@src/components/quran/SurahList";
import { ErrorDisplay } from "@src/components/common/ErrorDisplay";
import { ReciteHero } from "@src/components/recite/ReciteHero";
import { ListeningOverlay } from "@src/components/recite/ListeningOverlay";
import { useQuranData } from "@src/hooks/useQuranData";
import { useRecitationStore } from "@src/stores/recitationStore";
import { useFreeRecitation } from "@src/hooks/useFreeRecitation";
import { Surah } from "@src/domain/models/Surah";

interface FoundInfo {
  surah: Surah;
  ayahNumber: number;
}

export default function HomeScreen() {
  const { surahs, isLoading, error, loadSurahs } = useQuranData();
  const { setSelectedSurah } = useRecitationStore();
  const router = useRouter();
  const [foundInfo, setFoundInfo] = useState<FoundInfo | null>(null);
  const colors = useThemeColors();

  useEffect(() => {
    loadSurahs();
  }, [loadSurahs]);

  const handleFound = useCallback(() => {
    const state = useRecitationStore.getState();
    if (state.currentSurahId == null) return;

    const surah = surahs.find((s) => s.id === state.currentSurahId);
    if (!surah) return;

    setFoundInfo({
      surah,
      ayahNumber: state.currentAyahNumber ?? 1,
    });

    const ayah = state.currentAyahNumber ?? 1;
    setTimeout(() => {
      setSelectedSurah(surah);
      router.push(`/surah/${surah.id}?ayah=${ayah}`);
      setTimeout(() => setFoundInfo(null), 300);
    }, 700);
  }, [surahs, setSelectedSurah, router]);

  const {
    isListening,
    connectionStatus,
    isConnecting,
    startListening,
    stopListening,
  } = useFreeRecitation(handleFound);

  const handleSelectSurah = (surah: Surah) => {
    setSelectedSurah(surah);
    router.push(`/surah/${surah.id}`);
  };

  return (
    <View className="flex-1 bg-ivory dark:bg-d-bg">
      <SafeAreaView className="flex-1">
        <View className="flex-row items-center justify-between px-5 pb-3 pt-2">
          <Text
            className="text-3xl text-primary-500 dark:text-primary-300"
            style={{ fontFamily: "Amiri" }}
          >
            Quran
          </Text>
          <Pressable
            className="h-11 w-11 items-center justify-center rounded-full"
            onPress={() => router.push("/settings")}
            accessibilityRole="button"
            accessibilityLabel="Open settings"
          >
            <Ionicons name="settings-outline" size={22} color={colors.gold[500]} />
          </Pressable>
        </View>

        <ReciteHero onPress={startListening} />

        {error ? (
          <ErrorDisplay message={error} onRetry={loadSurahs} />
        ) : (
          <SurahList
            surahs={surahs}
            isLoading={isLoading}
            onSelectSurah={handleSelectSurah}
          />
        )}
      </SafeAreaView>

      <ListeningOverlay
        visible={isListening || foundInfo != null}
        connectionStatus={connectionStatus}
        isConnecting={isConnecting}
        foundInfo={foundInfo}
        onCancel={stopListening}
      />
    </View>
  );
}
