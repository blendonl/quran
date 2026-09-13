import { View, Text, Pressable, StyleSheet } from "react-native";
import Animated, {
  useAnimatedStyle,
  useAnimatedReaction,
  useSharedValue,
  withRepeat,
  withDelay,
  withTiming,
  cancelAnimation,
  Easing,
  SharedValue,
} from "react-native-reanimated";
import { memo, useMemo } from "react";
import { Ionicons } from "@expo/vector-icons";
import { Surah } from "@src/domain/models/Surah";
import { useThemeColors, ThemeColors } from "@src/config/themeColors";

interface FoundInfo {
  surah: Surah;
  ayahNumber: number;
}

interface ListeningOverlayProps {
  visible: boolean;
  connectionStatus: string;
  isConnecting: boolean;
  foundInfo: FoundInfo | null;
  onCancel: () => void;
}

function createRingStyles(colors: ThemeColors): Record<number, object> {
  return {
    220: {
      position: "absolute" as const,
      width: 220,
      height: 220,
      borderRadius: 110,
      borderWidth: 1,
      borderColor: colors.gold[400],
    },
    150: {
      position: "absolute" as const,
      width: 150,
      height: 150,
      borderRadius: 75,
      borderWidth: 1,
      borderColor: colors.gold[400],
    },
  };
}

function createStyles(colors: ThemeColors) {
  return StyleSheet.create({
    overlay: {
      backgroundColor: `${colors.primary[950] ?? colors.primary[900]}F0`,
      alignItems: "center",
      justifyContent: "center",
      zIndex: 100,
    },
    ringContainer: {
      width: 240,
      height: 240,
      alignItems: "center",
      justifyContent: "center",
    },
    centerCircle: {
      width: 84,
      height: 84,
      borderRadius: 42,
      borderWidth: 2,
      borderColor: colors.gold[400],
      alignItems: "center",
      justifyContent: "center",
    },
    textContainer: {
      marginTop: 24,
      alignItems: "center",
    },
    arabicTitle: {
      fontFamily: "Amiri",
      fontSize: 22,
      color: colors.gold[400],
    },
    subtitle: {
      marginTop: 4,
      fontSize: 16,
      color: colors.surface.bg,
    },
    listeningTitle: {
      fontFamily: "Amiri",
      fontSize: 22,
      color: colors.surface.bg,
    },
    hint: {
      marginTop: 8,
      fontSize: 13,
      color: colors.primary[200],
    },
    statusRow: {
      flexDirection: "row",
      alignItems: "center",
      marginTop: 12,
    },
    statusDot: {
      width: 8,
      height: 8,
      borderRadius: 4,
    },
    statusText: {
      marginLeft: 6,
      fontSize: 11,
      color: colors.primary[300],
    },
    cancelBtn: {
      marginTop: 56,
      borderRadius: 999,
      borderWidth: 1,
      borderColor: `${colors.gold[500]}66`,
      paddingHorizontal: 40,
      paddingVertical: 12,
    },
    cancelText: {
      fontSize: 16,
      color: colors.gold[400],
    },
  });
}

const PulseRing = memo(function PulseRing({
  delay,
  size,
  active,
  ringStyle,
}: {
  delay: number;
  size: number;
  active: SharedValue<number>;
  ringStyle: object;
}) {
  const progress = useSharedValue(0);

  useAnimatedReaction(
    () => active.value,
    (val) => {
      if (val > 0.5) {
        progress.value = withDelay(
          delay,
          withRepeat(
            withTiming(1, { duration: 1400, easing: Easing.out(Easing.cubic) }),
            -1,
          ),
        );
      } else {
        cancelAnimation(progress);
        progress.value = 0;
      }
    },
  );

  const anim = useAnimatedStyle(() => {
    const p = progress.value;
    return {
      transform: [{ scale: 0.4 + p * 0.6 }],
      opacity: Math.max(0, 0.5 - p * 0.7),
    };
  });

  return <Animated.View style={[anim, ringStyle]} />;
});

export function ListeningOverlay({
  visible,
  connectionStatus,
  isConnecting,
  foundInfo,
  onCancel,
}: ListeningOverlayProps) {
  const colors = useThemeColors();
  const styles = useMemo(() => createStyles(colors), [colors]);
  const ringStyles = useMemo(() => createRingStyles(colors), [colors]);

  const show = useSharedValue(0);
  const active = useSharedValue(0);
  const isFound = foundInfo != null;

  useAnimatedReaction(
    () => (visible ? 1 : 0),
    (val) => {
      show.value = withTiming(val, { duration: 150 });
      active.value = val;
    },
  );

  useAnimatedReaction(
    () => (isFound ? 1 : 0),
    (val) => {
      if (val > 0.5) {
        active.value = 0;
      }
    },
  );

  const overlayStyle = useAnimatedStyle(() => ({
    opacity: show.value,
  }));

  const centerBg = isFound ? colors.primary[500] : colors.primary[700];

  return (
    <Animated.View
      style={[StyleSheet.absoluteFill, styles.overlay, overlayStyle]}
      pointerEvents={visible ? "auto" : "none"}
    >
      <View style={styles.ringContainer}>
        <PulseRing delay={0} size={220} active={active} ringStyle={ringStyles[220]} />
        <PulseRing delay={350} size={150} active={active} ringStyle={ringStyles[150]} />

        <View style={[styles.centerCircle, { backgroundColor: centerBg }]}>
          <Ionicons
            name={isFound ? "checkmark" : "mic"}
            size={38}
            color={colors.gold[400]}
          />
        </View>
      </View>

      {isFound ? (
        <View style={styles.textContainer}>
          <Text style={styles.arabicTitle}>{foundInfo.surah.nameArabic}</Text>
          <Text style={styles.subtitle}>
            {foundInfo.surah.nameSimple} — Ayah {foundInfo.ayahNumber}
          </Text>
        </View>
      ) : (
        <View style={styles.textContainer}>
          <Text style={styles.listeningTitle}>
            {isConnecting ? "Connecting..." : "Listening..."}
          </Text>
          <Text style={styles.hint}>Recite any verse from the Quran</Text>
          <View style={styles.statusRow}>
            <View
              style={[
                styles.statusDot,
                {
                  backgroundColor:
                    connectionStatus === "connected"
                      ? colors.connection.connected
                      : connectionStatus === "connecting"
                        ? colors.connection.connecting
                        : colors.connection.disconnected,
                },
              ]}
            />
            <Text style={styles.statusText}>
              {connectionStatus === "connected"
                ? "Connected"
                : connectionStatus === "connecting"
                  ? "Connecting"
                  : "Disconnected"}
            </Text>
          </View>
        </View>
      )}

      {!isFound && (
        <Pressable
          style={({ pressed }) => [
            styles.cancelBtn,
            { opacity: pressed ? 0.6 : 1 },
          ]}
          onPress={onCancel}
          accessibilityRole="button"
          accessibilityLabel="Cancel listening"
        >
          <Text style={styles.cancelText}>Cancel</Text>
        </Pressable>
      )}
    </Animated.View>
  );
}
