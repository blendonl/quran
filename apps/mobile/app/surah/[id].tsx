import { useEffect } from "react";
import { View, Text, Pressable } from "react-native";
import { useLocalSearchParams, useRouter, Stack } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { AyahSelector } from "@src/components/quran/AyahSelector";
import { ErrorDisplay } from "@src/components/common/ErrorDisplay";
import { useQuranData } from "@src/hooks/useQuranData";
import { useRecitationStore } from "@src/stores/recitationStore";
import { Ayah } from "@src/domain/models/Ayah";

export default function SurahDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const surahId = Number(id);
  const router = useRouter();

  const { ayahs, isLoading, error, loadAyahs } = useQuranData();
  const { selectedSurah, selectedAyah, setSelectedAyah } = useRecitationStore();

  useEffect(() => {
    if (surahId) {
      loadAyahs(surahId);
    }
  }, [surahId, loadAyahs]);

  const handleSelectAyah = (ayah: Ayah) => {
    setSelectedAyah(ayah);
  };

  const handleStartPractice = () => {
    if (selectedAyah) {
      router.push("/recite");
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-white" edges={["bottom"]}>
      <Stack.Screen
        options={{
          title: selectedSurah?.nameSimple ?? "Select Ayah",
        }}
      />

      {selectedSurah && (
        <View className="border-b border-gray-100 px-4 pb-3 pt-2">
          <Text
            className="text-xl text-gray-800"
            style={{ fontFamily: "Amiri", writingDirection: "rtl", textAlign: "center" }}
          >
            {selectedSurah.nameArabic}
          </Text>
          <Text className="text-center text-xs text-gray-500">
            {selectedSurah.versesCount} verses · {selectedSurah.revelationPlace}
          </Text>
        </View>
      )}

      {error ? (
        <ErrorDisplay message={error} onRetry={() => loadAyahs(surahId)} />
      ) : (
        <AyahSelector
          ayahs={ayahs}
          selectedAyah={selectedAyah}
          isLoading={isLoading}
          onSelectAyah={handleSelectAyah}
        />
      )}

      {selectedAyah && (
        <View className="border-t border-gray-100 px-4 pb-4 pt-3">
          <Pressable
            className="items-center rounded-xl bg-primary-600 py-4"
            onPress={handleStartPractice}
          >
            <Text className="text-base font-bold text-white">Practice This Ayah</Text>
          </Pressable>
        </View>
      )}
    </SafeAreaView>
  );
}
