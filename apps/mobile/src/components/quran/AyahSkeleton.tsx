import { useEffect } from "react";
import { View } from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
} from "react-native-reanimated";

function SkeletonCard() {
  const opacity = useSharedValue(0.3);

  useEffect(() => {
    opacity.value = withRepeat(
      withTiming(0.7, { duration: 900 }),
      -1,
      true,
    );
  }, [opacity]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
  }));

  return (
    <Animated.View
      className="mb-3 rounded-2xl bg-surface-card px-5 py-4 dark:bg-d-card"
      style={animatedStyle}
    >
      <View className="mb-3 flex-row-reverse items-center">
        <View className="h-8 w-8 rounded-full bg-gold-100 dark:bg-gold-800" />
      </View>
      <View className="flex-row-reverse flex-wrap gap-y-3">
        <View className="mr-2 h-5 w-24 rounded bg-gold-50 dark:bg-gold-900" />
        <View className="mr-2 h-5 w-32 rounded bg-gold-50 dark:bg-gold-900" />
        <View className="mr-2 h-5 w-20 rounded bg-gold-50 dark:bg-gold-900" />
        <View className="mr-2 h-5 w-28 rounded bg-gold-50 dark:bg-gold-900" />
        <View className="mr-2 h-5 w-16 rounded bg-gold-50 dark:bg-gold-900" />
      </View>
    </Animated.View>
  );
}

export function AyahSkeletonList() {
  return (
    <View className="flex-1 bg-ivory px-4 pt-3 dark:bg-d-bg">
      {Array.from({ length: 8 }, (_, i) => (
        <SkeletonCard key={i} />
      ))}
    </View>
  );
}
