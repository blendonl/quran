import { useEffect } from "react";
import { View, Text } from "react-native";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { SurahList } from "@src/components/quran/SurahList";
import { ErrorDisplay } from "@src/components/common/ErrorDisplay";
import { useQuranData } from "@src/hooks/useQuranData";
import { useRecitationStore } from "@src/stores/recitationStore";
import { Surah } from "@src/domain/models/Surah";

export default function QuranScreen() {
  const { surahs, isLoading, error, loadSurahs } = useQuranData();
  const { setSelectedSurah } = useRecitationStore();
  const router = useRouter();

  useEffect(() => {
    loadSurahs();
  }, [loadSurahs]);

  const handleSelectSurah = (surah: Surah) => {
    setSelectedSurah(surah);
    router.push(`/surah/${surah.id}`);
  };

  return (
    <SafeAreaView className="flex-1 bg-white" edges={["bottom"]}>
      <View className="border-b border-gray-100 px-4 pb-3 pt-2">
        <Text className="text-lg font-bold text-gray-900">Select a Surah</Text>
        <Text className="text-xs text-gray-500">Choose a surah to practice reciting</Text>
      </View>

      {error ? (
        <ErrorDisplay message={error} onRetry={loadSurahs} />
      ) : (
        <SurahList surahs={surahs} isLoading={isLoading} onSelectSurah={handleSelectSurah} />
      )}
    </SafeAreaView>
  );
}
