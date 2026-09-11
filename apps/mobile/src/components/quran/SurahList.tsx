import { FlatList, View, Text } from "react-native";
import { Surah } from "../../domain/models/Surah";
import { SurahListItem } from "./SurahListItem";
import { LoadingSpinner } from "../common/LoadingSpinner";

interface SurahListProps {
  surahs: Surah[];
  isLoading: boolean;
  onSelectSurah: (surah: Surah) => void;
}

export function SurahList({ surahs, isLoading, onSelectSurah }: SurahListProps) {
  if (isLoading) {
    return <LoadingSpinner message="Loading surahs..." />;
  }

  if (surahs.length === 0) {
    return (
      <View className="flex-1 items-center justify-center p-4">
        <Text className="text-base text-ink-muted dark:text-d-ink-muted">No surahs available</Text>
      </View>
    );
  }

  return (
    <FlatList
      data={surahs}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => <SurahListItem surah={item} onPress={onSelectSurah} />}
      showsVerticalScrollIndicator={false}
    />
  );
}
