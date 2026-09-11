import { FlatList, Pressable, View, Text } from "react-native";
import { Ayah } from "../../domain/models/Ayah";
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
      className={`border-b border-gray-100 px-4 py-3 ${isSelected ? "bg-primary-50" : "active:bg-gray-50"}`}
      onPress={() => onPress(ayah)}
    >
      <View className="flex-row items-start">
        <View
          className={`mr-3 h-8 w-8 items-center justify-center rounded-full ${isSelected ? "bg-primary-500" : "bg-gray-200"}`}
        >
          <Text
            className={`text-xs font-bold ${isSelected ? "text-white" : "text-gray-600"}`}
          >
            {ayah.verseNumber}
          </Text>
        </View>
        <View className="flex-1">
          <Text
            className="text-xl leading-10 text-gray-900"
            style={{ fontFamily: "Amiri", writingDirection: "rtl", textAlign: "right" }}
          >
            {ayah.textUthmani}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}
