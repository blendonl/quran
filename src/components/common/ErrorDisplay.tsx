import { View, Text, Pressable } from "react-native";

interface ErrorDisplayProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorDisplay({ message, onRetry }: ErrorDisplayProps) {
  return (
    <View className="flex-1 items-center justify-center p-6">
      <Text className="mb-2 text-lg font-semibold text-red-600">Error</Text>
      <Text className="mb-4 text-center text-base text-gray-700">{message}</Text>
      {onRetry && (
        <Pressable
          className="rounded-lg bg-primary-600 px-6 py-3"
          onPress={onRetry}
        >
          <Text className="text-base font-semibold text-white">Retry</Text>
        </Pressable>
      )}
    </View>
  );
}
