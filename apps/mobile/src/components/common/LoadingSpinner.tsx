import { View, ActivityIndicator, Text } from "react-native";

interface LoadingSpinnerProps {
  message?: string;
  size?: "small" | "large";
}

export function LoadingSpinner({ message, size = "large" }: LoadingSpinnerProps) {
  return (
    <View className="flex-1 items-center justify-center p-4">
      <ActivityIndicator size={size} color="#2f9568" />
      {message && <Text className="mt-3 text-base text-gray-600">{message}</Text>}
    </View>
  );
}
