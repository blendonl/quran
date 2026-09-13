import { useEffect } from "react";
import { View, Text, Pressable } from "react-native";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
  withRepeat,
  withSequence,
  cancelAnimation,
} from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useThemeColors } from "@src/config/themeColors";
import { ConnectionStatus } from "../common/ConnectionStatus";

type ConnectionStatusType = "disconnected" | "connecting" | "connected" | "error";

interface ReciteActionBarProps {
  selectedAyahNumber: number | null;
  isStreaming: boolean;
  isConnecting: boolean;
  isDisabled: boolean;
  connectionStatus: ConnectionStatusType;
  recitationMode: "following" | "learning";
  onStart: () => void;
  onStop: () => void;
  onToggleMode: () => void;
}

const BAR_HEIGHT = 80;

export function ReciteActionBar({
  selectedAyahNumber,
  isStreaming,
  isConnecting,
  isDisabled,
  connectionStatus,
  recitationMode,
  onStart,
  onStop,
  onToggleMode,
}: ReciteActionBarProps) {
  const insets = useSafeAreaInsets();
  const colors = useThemeColors();
  const visible = selectedAyahNumber != null || isStreaming || isConnecting;
  const translateY = useSharedValue(BAR_HEIGHT + insets.bottom + 20);
  const pulseScale = useSharedValue(1);

  useEffect(() => {
    translateY.value = withTiming(visible ? 0 : BAR_HEIGHT + insets.bottom + 20, {
      duration: 250,
    });
  }, [visible, insets.bottom, translateY]);

  useEffect(() => {
    if (isStreaming) {
      pulseScale.value = withRepeat(
        withSequence(
          withTiming(1.08, { duration: 800 }),
          withTiming(1, { duration: 800 }),
        ),
        -1,
        true,
      );
    } else {
      cancelAnimation(pulseScale);
      pulseScale.value = withTiming(1, { duration: 200 });
    }
  }, [isStreaming, pulseScale]);

  const barAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
  }));

  const buttonAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulseScale.value }],
  }));

  const buttonColor = isStreaming
    ? "bg-red-500"
    : isDisabled
      ? "bg-gray-400"
      : "bg-primary-500";

  const label = isConnecting
    ? "Connecting..."
    : isStreaming
      ? "Listening..."
      : `Recite from Ayah ${selectedAyahNumber}`;

  const showConnectionStatus = isStreaming || isConnecting;
  const sessionActive = isStreaming || isConnecting;
  const modeIcon = recitationMode === "following" ? "eye-outline" : "school-outline";
  const modeLabel = recitationMode === "following" ? "Following" : "Learning";

  return (
    <Animated.View
      className="absolute bottom-0 left-0 right-0 border-t border-surface-sep bg-ivory dark:border-d-sep dark:bg-d-bg"
      style={[
        {
          paddingBottom: insets.bottom || 16,
          shadowColor: colors.ink.base,
          shadowOffset: { width: 0, height: -2 },
          shadowOpacity: 0.08,
          shadowRadius: 8,
          elevation: 8,
        },
        barAnimatedStyle,
      ]}
      pointerEvents={visible ? "auto" : "none"}
    >
      <View className="flex-row items-center justify-between px-5 pb-1 pt-3.5">
        <View className="flex-1">
          <Text className="text-[15px] font-semibold text-primary-500 dark:text-primary-300">{label}</Text>
          {showConnectionStatus && (
            <View className="mt-1 flex-row items-center gap-3">
              <ConnectionStatus status={connectionStatus} />
              <Pressable
                className="flex-row items-center gap-1 rounded-full bg-primary-50 px-2.5 py-1 dark:bg-primary-950"
                onPress={onToggleMode}
                accessibilityRole="button"
                accessibilityLabel={`Switch to ${recitationMode === "following" ? "learning" : "following"} mode`}
              >
                <Ionicons name={modeIcon as any} size={14} color={colors.primary[500]} />
                <Text className="text-xs font-medium text-primary-500 dark:text-primary-300">{modeLabel}</Text>
              </Pressable>
            </View>
          )}
        </View>
        <Animated.View style={buttonAnimatedStyle}>
          {isStreaming ? (
            <Pressable
              className="h-12 w-12 items-center justify-center rounded-full bg-red-500"
              onPress={onStop}
              accessibilityRole="button"
              accessibilityLabel="Stop recitation"
            >
              <Ionicons name="stop" size={22} color="white" />
            </Pressable>
          ) : (
            <Pressable
              className={`h-12 w-12 items-center justify-center rounded-full ${buttonColor}`}
              onPress={onStart}
              disabled={isDisabled || isConnecting}
              accessibilityRole="button"
              accessibilityLabel="Start recitation"
              accessibilityState={{ disabled: isDisabled || isConnecting }}
            >
              {isConnecting ? (
                <Ionicons name="cloud-upload-outline" size={22} color="white" />
              ) : (
                <Ionicons name="mic" size={22} color="white" />
              )}
            </Pressable>
          )}
        </Animated.View>
      </View>
    </Animated.View>
  );
}
