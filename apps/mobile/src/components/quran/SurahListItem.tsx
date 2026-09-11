import { Pressable, View, Text } from "react-native";
import { Surah } from "../../domain/models/Surah";

interface SurahListItemProps {
  surah: Surah;
  onPress: (surah: Surah) => void;
}

export function SurahListItem({ surah, onPress }: SurahListItemProps) {
  return (
    <Pressable
      className="flex-row items-center border-b border-gray-100 px-4 py-3 active:bg-gray-50"
      onPress={() => onPress(surah)}
    >
      <View className="mr-3 h-10 w-10 items-center justify-center rounded-lg bg-primary-100">
        <Text className="text-sm font-bold text-primary-700">{surah.id}</Text>
      </View>

      <View className="flex-1">
        <Text className="text-base font-semibold text-gray-900">{surah.nameSimple}</Text>
        <Text className="text-xs text-gray-500">
          {surah.translatedName.name} · {surah.versesCount} verses
        </Text>
      </View>

      <Text
        className="text-xl text-gray-800"
        style={{ fontFamily: "Amiri", writingDirection: "rtl" }}
      >
        {surah.nameArabic}
      </Text>
    </Pressable>
  );
}
