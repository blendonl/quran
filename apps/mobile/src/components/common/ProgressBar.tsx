import { View, Text } from "react-native";

interface ProgressBarProps {
  progress: number;
  label?: string;
}

export function ProgressBar({ progress, label }: ProgressBarProps) {
  const percentage = Math.round(progress * 100);

  return (
    <View className="w-full px-4">
      {label && <Text className="mb-2 text-sm text-gray-600">{label}</Text>}
      <View className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
        <View
          className="h-full rounded-full bg-primary-500"
          style={{ width: `${percentage}%` }}
        />
      </View>
      <Text className="mt-1 text-right text-xs text-gray-500">{percentage}%</Text>
    </View>
  );
}
