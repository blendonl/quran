import { View, Text } from "react-native";
import { ElongationResult } from "../../domain/models/ElongationResult";

interface ElongatedTextDisplayProps {
  result: ElongationResult;
  size?: "md" | "lg" | "xl";
}

const sizeMap = {
  md: 24,
  lg: 32,
  xl: 40,
};

export function ElongatedTextDisplay({ result, size = "lg" }: ElongatedTextDisplayProps) {
  const fontSize = sizeMap[size];

  return (
    <View className="w-full px-4">
      <View className="flex-row-reverse flex-wrap justify-end">
        {result.characters.map((char, index) => (
          <Text
            key={index}
            style={{
              fontSize,
              writingDirection: "rtl",
              color: char.isElongated ? "#de9a22" : "#1a1a1a",
              fontFamily: "Amiri",
              lineHeight: fontSize * 1.8,
            }}
          >
            {char.displayed}
          </Text>
        ))}
      </View>
    </View>
  );
}
