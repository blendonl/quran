import { Pressable, View, Text } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useThemeColors } from "@src/config/themeColors";

interface ReciteHeroProps {
  onPress: () => void;
}

export function ReciteHero({ onPress }: ReciteHeroProps) {
  const colors = useThemeColors();

  return (
    <Pressable
      onPress={onPress}
      className="mx-5 mb-4"
      style={({ pressed }) => ({ opacity: pressed ? 0.85 : 1 })}
      accessibilityRole="button"
      accessibilityLabel="Start reciting any verse"
    >
      <View className="overflow-hidden rounded-2xl bg-primary-500">
        <View className="absolute -right-10 -top-10 h-36 w-36 rounded-full bg-primary-400 opacity-15" />
        <View className="absolute -bottom-8 -left-8 h-28 w-28 rounded-full bg-gold-500 opacity-10" />
        <View className="absolute bottom-0 right-4 top-0 justify-center opacity-5">
          <Text
            style={{ fontFamily: "Amiri", fontSize: 72, color: colors.surface.bg }}
          >
            ﷽
          </Text>
        </View>

        <View className="flex-row items-center px-5 py-5">
          <View className="h-14 w-14 items-center justify-center rounded-full border-[1.5px] border-gold-400 bg-primary-700">
            <Ionicons name="mic" size={24} color={colors.gold[400]} />
          </View>

          <View className="ml-4 flex-1">
            <Text
              className="text-xl text-ivory"
              style={{ fontFamily: "Amiri" }}
            >
              Recite
            </Text>
            <Text className="mt-0.5 text-xs text-primary-200">
              Start reciting any verse — we'll find your place
            </Text>
          </View>

          <View className="h-8 w-8 items-center justify-center rounded-full bg-primary-600">
            <Ionicons name="chevron-forward" size={16} color={colors.gold[400]} />
          </View>
        </View>
      </View>
    </Pressable>
  );
}
