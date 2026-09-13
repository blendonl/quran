import { View, Text } from "react-native";
import { RecitationResult, WordMatchStatus } from "../../domain/models/RecitationResult";

interface AyahComparisonProps {
  result: RecitationResult;
}

const statusColors: Record<WordMatchStatus, string> = {
  correct: "#2f9568",
  incorrect: "#dc2626",
  missing: "#9ca3af",
  extra: "#f59e0b",
};

export function AyahComparison({ result }: AyahComparisonProps) {
  const percentage = Math.round(result.accuracy * 100);

  return (
    <View className="w-full px-4">
      <View className="mb-3 flex-row items-center justify-between">
        <Text className="text-sm text-gray-500">Accuracy</Text>
        <Text
          className="text-lg font-bold"
          style={{ color: result.accuracy >= 0.8 ? "#2f9568" : "#dc2626" }}
        >
          {percentage}%
        </Text>
      </View>

      <View className="flex-row-reverse flex-wrap justify-end gap-1">
        {result.wordMatches.map((match, index) => (
          <Text
            key={index}
            style={{
              fontSize: 24,
              color: statusColors[match.status],
              fontFamily: "Amiri",
              writingDirection: "rtl",
              textDecorationLine: match.status === "missing" ? "line-through" : "none",
              opacity: match.status === "missing" ? 0.6 : 1,
            }}
          >
            {match.word}
          </Text>
        ))}
      </View>

      <View className="mt-4 flex-row justify-center gap-4">
        <Legend color="#2f9568" label="Correct" />
        <Legend color="#dc2626" label="Incorrect" />
        <Legend color="#9ca3af" label="Missing" />
        <Legend color="#f59e0b" label="Extra" />
      </View>
    </View>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <View className="flex-row items-center gap-1">
      <View className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
      <Text className="text-xs text-gray-600">{label}</Text>
    </View>
  );
}
