import { View, ActivityIndicator, Text } from "react-native";
import { useThemeColors } from "../../config/themeColors";

interface LoadingSpinnerProps {
  message?: string;
  size?: "small" | "large";
}

export function LoadingSpinner({ message, size = "large" }: LoadingSpinnerProps) {
  const colors = useThemeColors();

  return (
    <View className="flex-1 items-center justify-center p-4">
      <ActivityIndicator size={size} color={colors.primary[500]} />
      {message && <Text className="mt-3 text-base text-ink-secondary dark:text-d-ink-secondary">{message}</Text>}
    </View>
  );
}
