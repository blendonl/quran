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
          withTiming(1.06, { duration: 900 }),
          withTiming(1, { duration: 900 }),
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

  const buttonColor = isRecording ? "bg-red-500" : isDisabled ? "bg-gray-400" : "bg-primary-500";
  const iconName = isRecording ? "stop" : "mic";
  const label = isProcessing ? "Connecting..." : isRecording ? "Tap to Stop" : "Tap to Recite";

  return (
    <View className="items-center">
      <Animated.View style={animatedStyle}>
        <View className="rounded-full border-2 border-gold-400 p-1">
          <Pressable
            className={`h-20 w-20 items-center justify-center rounded-full ${buttonColor} shadow-lg`}
            onPress={onPress}
            disabled={isDisabled || isProcessing}
            accessibilityRole="button"
            accessibilityLabel={label}
            accessibilityState={{ disabled: isDisabled || isProcessing }}
          >
            {isProcessing ? (
              <Ionicons name="cloud-upload-outline" size={32} color="white" />
            ) : (
              <Ionicons name={iconName} size={32} color="white" />
            )}
          </Pressable>
        </View>
      </Animated.View>
      <Text className="mt-2 text-xs text-gold-600 dark:text-gold-400">{label}</Text>
    </View>
  );
}
