import { Pressable, View, Text } from "react-native";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
  withSequence,
  cancelAnimation,
} from "react-native-reanimated";
import { useEffect } from "react";
import { Ionicons } from "@expo/vector-icons";

interface RecordButtonProps {
  isRecording: boolean;
  isProcessing: boolean;
  isDisabled: boolean;
  onPress: () => void;
}

export function RecordButton({ isRecording, isProcessing, isDisabled, onPress }: RecordButtonProps) {
  const pulseScale = useSharedValue(1);

  useEffect(() => {
    if (isRecording) {
      pulseScale.value = withRepeat(
        withSequence(
          withTiming(1.15, { duration: 800 }),
          withTiming(1, { duration: 800 }),
        ),
        -1,
        true,
      );
    } else {
      cancelAnimation(pulseScale);
      pulseScale.value = withTiming(1, { duration: 200 });
    }
  }, [isRecording, pulseScale]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulseScale.value }],
  }));

  const buttonColor = isRecording ? "bg-red-500" : isDisabled ? "bg-gray-400" : "bg-primary-600";
  const iconName = isRecording ? "stop" : "mic";
  const label = isProcessing ? "Processing..." : isRecording ? "Tap to Stop" : "Tap to Recite";

  return (
    <View className="items-center">
      <Animated.View style={animatedStyle}>
        <Pressable
          className={`h-20 w-20 items-center justify-center rounded-full ${buttonColor} shadow-lg`}
          onPress={onPress}
          disabled={isDisabled || isProcessing}
        >
          {isProcessing ? (
            <Ionicons name="hourglass-outline" size={32} color="white" />
          ) : (
            <Ionicons name={iconName} size={32} color="white" />
          )}
        </Pressable>
      </Animated.View>
      <Text className="mt-3 text-sm text-gray-600">{label}</Text>
    </View>
  );
}
