import { FlatList, Pressable, View, Text } from "react-native";
import { Ayah } from "../../domain/models/Ayah";
import { RTL_TEXT } from "../../config/themeColors";
import { LoadingSpinner } from "../common/LoadingSpinner";

interface AyahSelectorProps {
  ayahs: Ayah[];
  selectedAyah: Ayah | null;
  isLoading: boolean;
  onSelectAyah: (ayah: Ayah) => void;
}

export function AyahSelector({ ayahs, selectedAyah, isLoading, onSelectAyah }: AyahSelectorProps) {
  if (isLoading) {
    return <LoadingSpinner message="Loading ayahs..." size="small" />;
  }

  return (
    <FlatList
      data={ayahs}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => (
        <AyahItem
          ayah={item}
          isSelected={selectedAyah?.id === item.id}
          onPress={onSelectAyah}
        />
      )}
      showsVerticalScrollIndicator={false}
    />
  );
}

interface AyahItemProps {
  ayah: Ayah;
  isSelected: boolean;
  onPress: (ayah: Ayah) => void;
}

function AyahItem({ ayah, isSelected, onPress }: AyahItemProps) {
  return (
    <Pressable
      className={`border-b border-surface-sep px-4 py-3 dark:border-d-sep ${isSelected ? "bg-primary-50 dark:bg-primary-950" : "active:bg-surface-elevated dark:active:bg-d-elevated"}`}
      onPress={() => onPress(ayah)}
    >
      <View className="flex-row items-start">
        <View
          className={`mr-3 h-8 w-8 items-center justify-center rounded-full ${isSelected ? "bg-primary-500" : "bg-surface-elevated dark:bg-d-elevated"}`}
        >
          <Text
            className={`text-xs font-bold ${isSelected ? "text-white" : "text-ink-secondary dark:text-d-ink-secondary"}`}
          >
            {ayah.verseNumber}
          </Text>
        </View>
        <View className="flex-1">
          <Text
            className="text-xl leading-10 text-ink dark:text-d-ink"
            style={{ fontFamily: "Amiri", ...RTL_TEXT, textAlign: "right" }}
          >
            {ayah.textUthmani}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}
