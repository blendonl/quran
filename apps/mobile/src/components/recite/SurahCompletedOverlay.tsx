import { useEffect, useMemo } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
  withDelay,
  withSpring,
} from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useThemeColors, ThemeColors } from "@src/config/themeColors";

interface SurahCompletedBannerProps {
  visible: boolean;
  nextSurahId: number | null;
  onContinue: () => void;
  onDone: () => void;
  onDismiss: () => void;
}

const BANNER_HEIGHT = 140;

function createStyles(colors: ThemeColors) {
  return StyleSheet.create({
    container: {
      position: "absolute",
      bottom: 0,
      left: 0,
      right: 0,
      backgroundColor: colors.surface.bg,
      borderTopWidth: 1,
      borderTopColor: `${colors.gold[300]}59`,
      paddingHorizontal: 20,
      paddingTop: 16,
      shadowColor: colors.primary[500],
      shadowOffset: { width: 0, height: -4 },
      shadowOpacity: 0.1,
      shadowRadius: 12,
      elevation: 10,
    },
    topRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 12,
    },
    checkBadge: {
      width: 36,
      height: 36,
      borderRadius: 18,
      backgroundColor: colors.primary[500],
      alignItems: "center",
      justifyContent: "center",
    },
    textGroup: {
      flex: 1,
      flexDirection: "row",
      alignItems: "baseline",
      gap: 8,
    },
    title: {
      fontSize: 16,
      fontWeight: "600",
      color: colors.primary[500],
    },
    subtitle: {
      fontSize: 14,
      color: colors.gold[500],
      fontFamily: "Amiri",
    },
    closeBtn: {
      width: 44,
      height: 44,
      borderRadius: 22,
      backgroundColor: `${colors.gold[600]}14`,
      alignItems: "center",
      justifyContent: "center",
    },
    actions: {
      flexDirection: "row",
      gap: 10,
      marginTop: 14,
    },
    continueBtn: {
      flex: 1,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 6,
      backgroundColor: colors.primary[500],
      paddingVertical: 11,
      borderRadius: 10,
    },
    continueText: {
      fontSize: 14,
      fontWeight: "600",
      color: colors.surface.bg,
    },
    doneBtn: {
      flex: 1,
      alignItems: "center",
      justifyContent: "center",
      paddingVertical: 11,
      borderRadius: 10,
      borderWidth: 1,
      borderColor: `${colors.primary[500]}33`,
    },
    doneText: {
      fontSize: 14,
      fontWeight: "600",
      color: colors.primary[500],
    },
    pressed: {
      opacity: 0.7,
    },
  });
}

export function SurahCompletedOverlay({
  visible,
  nextSurahId,
  onContinue,
  onDone,
  onDismiss,
}: SurahCompletedBannerProps) {
  const insets = useSafeAreaInsets();
  const colors = useThemeColors();
  const styles = useMemo(() => createStyles(colors), [colors]);

  const translateY = useSharedValue(BANNER_HEIGHT + insets.bottom + 40);
  const checkScale = useSharedValue(0);

  useEffect(() => {
    if (visible) {
      translateY.value = withSpring(0, { damping: 18, stiffness: 140 });
      checkScale.value = withDelay(150, withSpring(1, { damping: 12, stiffness: 200 }));
    } else {
      translateY.value = withTiming(BANNER_HEIGHT + insets.bottom + 40, { duration: 200 });
      checkScale.value = withTiming(0, { duration: 150 });
    }
  }, [visible, insets.bottom, translateY, checkScale]);

  const bannerStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
  }));

  const checkStyle = useAnimatedStyle(() => ({
    transform: [{ scale: checkScale.value }],
  }));

  return (
    <Animated.View
      style={[
        styles.container,
        { paddingBottom: insets.bottom || 16 },
        bannerStyle,
      ]}
      pointerEvents={visible ? "auto" : "none"}
    >
      <View style={styles.topRow}>
        <Animated.View style={[styles.checkBadge, checkStyle]}>
          <Ionicons name="checkmark" size={16} color={colors.surface.bg} />
        </Animated.View>

        <View style={styles.textGroup}>
          <Text style={styles.title}>Surah completed</Text>
          <Text style={styles.subtitle}>ما شاء الله</Text>
        </View>

        <Pressable
          style={styles.closeBtn}
          onPress={onDismiss}
          hitSlop={12}
          accessibilityRole="button"
          accessibilityLabel="Dismiss"
        >
          <Ionicons name="close" size={18} color={colors.gold[600]} />
        </Pressable>
      </View>

      <View style={styles.actions}>
        {nextSurahId != null && (
          <Pressable
            style={({ pressed }) => [styles.continueBtn, pressed && styles.pressed]}
            onPress={onContinue}
            accessibilityRole="button"
            accessibilityLabel="Continue to next surah"
          >
            <Text style={styles.continueText}>Next surah</Text>
            <Ionicons name="arrow-forward" size={14} color={colors.surface.bg} />
          </Pressable>
        )}

        <Pressable
          style={({ pressed }) => [styles.doneBtn, pressed && styles.pressed]}
          onPress={onDone}
          accessibilityRole="button"
          accessibilityLabel="Done"
        >
          <Text style={styles.doneText}>Done</Text>
        </Pressable>
      </View>
    </Animated.View>
  );
}
