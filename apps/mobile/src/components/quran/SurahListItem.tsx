import { Pressable, View, Text } from "react-native";
import { Surah } from "../../domain/models/Surah";
import { RTL_TEXT } from "../../config/themeColors";

interface SurahListItemProps {
  surah: Surah;
  onPress: (surah: Surah) => void;
}

export function SurahListItem({ surah, onPress }: SurahListItemProps) {
  return (
    <Pressable
      className="flex-row items-center border-b border-surface-sep px-5 py-4 active:bg-cream dark:border-d-sep dark:active:bg-d-card-alt"
      onPress={() => onPress(surah)}
      accessibilityRole="button"
      accessibilityLabel={`${surah.nameSimple}, ${surah.translatedName.name}, ${surah.versesCount} verses`}
    >
      <View className="mr-4 h-10 w-10 items-center justify-center rounded-full bg-gold-50 dark:bg-gold-900">
        <Text className="text-sm font-bold text-gold-500 dark:text-gold-300">{surah.id}</Text>
      </View>

      <View className="flex-1">
        <Text className="text-base font-semibold text-ink dark:text-d-ink">
          {surah.nameSimple}
        </Text>
        <Text className="text-xs text-gold-600 dark:text-gold-400">
          {surah.translatedName.name} · {surah.versesCount} verses
        </Text>
      </View>

      <Text
        className="text-2xl text-primary-500 dark:text-primary-300"
        style={{ fontFamily: "Amiri", ...RTL_TEXT }}
      >
        {surah.nameArabic}
      </Text>
    </Pressable>
  );
}
