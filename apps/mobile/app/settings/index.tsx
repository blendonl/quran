import { View, Text, TextInput, ScrollView, Switch, Pressable } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import Slider from "@react-native-community/slider";
import { useSettingsStore, MIN_FONT_SIZE, MAX_FONT_SIZE, ColorScheme } from "@src/stores/settingsStore";
import { useThemeColors, RTL_TEXT } from "@src/config/themeColors";
import { STREAMING_CONFIG, type GainMode } from "@src/config/streamingConfig";

const THEME_OPTIONS: { value: ColorScheme; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { value: "light", label: "Light", icon: "sunny" },
  { value: "dark", label: "Dark", icon: "moon" },
  { value: "system", label: "System", icon: "phone-portrait-outline" },
];

const GAIN_OPTIONS: { value: GainMode; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { value: "near", label: "Near", icon: "mic" },
  { value: "far", label: "Mosque", icon: "volume-high" },
];

export default function SettingsScreen() {
  const {
    serverUrl,
    setServerUrl,
    fontSize,
    setFontSize,
    showTranslation,
    setShowTranslation,
    colorScheme,
    setColorScheme,
    gainMode,
    setGainMode,
  } = useSettingsStore();
  const router = useRouter();
  const colors = useThemeColors();

  return (
    <SafeAreaView className="flex-1 bg-ivory dark:bg-d-bg">
      <View className="flex-row items-center px-4 pb-3 pt-2">
        <Pressable onPress={() => router.back()} accessibilityLabel="Go back" className="mr-3">
          <Ionicons name="chevron-back" size={24} color={colors.ink.base} />
        </Pressable>
        <Text
          className="text-2xl text-primary-500 dark:text-primary-300"
          style={{ fontFamily: "Amiri" }}
        >
          Settings
        </Text>
      </View>
      <ScrollView className="flex-1 px-5">

        <View className="mb-6">
          <Text className="mb-1 text-base font-semibold text-primary-800 dark:text-primary-200">Theme</Text>
          <Text className="mb-2 text-xs text-gold-600 dark:text-gold-400">Choose light, dark, or match device</Text>
          <View className="flex-row rounded-xl border border-primary-100 bg-surface-card p-1 dark:border-primary-800 dark:bg-d-card">
            {THEME_OPTIONS.map((opt) => {
              const isActive = colorScheme === opt.value;
              return (
                <Pressable
                  key={opt.value}
                  className={`flex-1 flex-row items-center justify-center rounded-lg py-2.5 ${isActive ? "bg-primary-500" : ""}`}
                  onPress={() => setColorScheme(opt.value)}
                  accessibilityRole="button"
                  accessibilityLabel={`${opt.label} theme`}
                  accessibilityState={{ selected: isActive }}
                >
                  <Ionicons
                    name={opt.icon}
                    size={16}
                    color={isActive ? "#FFFFFF" : colors.ink.muted}
                  />
                  <Text
                    className={`ml-1.5 text-sm font-medium ${isActive ? "text-ivory" : "text-ink-muted dark:text-d-ink-muted"}`}
                  >
                    {opt.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        <View className="mb-6">
          <Text className="mb-1 text-base font-semibold text-primary-800 dark:text-primary-200">Font Size</Text>
          <Text className="mb-2 text-xs text-gold-600 dark:text-gold-400">Adjust Arabic text size</Text>
          <View className="rounded-xl border border-primary-100 bg-surface-card px-4 py-3 dark:border-primary-800 dark:bg-d-card">
            <View className="mb-2 flex-row items-center justify-between">
              <Text className="text-sm text-ink-muted dark:text-d-ink-muted">{MIN_FONT_SIZE}px</Text>
              <Text className="text-sm font-semibold text-primary-500 dark:text-primary-300">{fontSize}px</Text>
              <Text className="text-sm text-ink-muted dark:text-d-ink-muted">{MAX_FONT_SIZE}px</Text>
            </View>
            <Slider
              style={{ width: "100%" }}
              minimumValue={MIN_FONT_SIZE}
              maximumValue={MAX_FONT_SIZE}
              step={1}
              value={fontSize}
              onValueChange={setFontSize}
              minimumTrackTintColor={colors.gold[500]}
              maximumTrackTintColor={colors.surface.separator}
              thumbTintColor={colors.gold[500]}
            />
            <Text
              className="mt-2 text-center text-ink-secondary dark:text-d-ink-secondary"
              style={{ fontSize, fontFamily: "Amiri", ...RTL_TEXT }}
            >
              بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ
            </Text>
          </View>
        </View>

        <View className="mb-6">
          <Text className="mb-1 text-base font-semibold text-primary-800 dark:text-primary-200">Translation</Text>
          <Text className="mb-2 text-xs text-gold-600 dark:text-gold-400">Show English translation below each ayah</Text>
          <View className="mb-3 rounded-xl border border-primary-100 bg-surface-card px-4 py-3 dark:border-primary-800 dark:bg-d-card">
            <View className="flex-row items-center justify-between">
              <Text className="text-sm text-ink dark:text-d-ink">Show Translation</Text>
              <Switch
                value={showTranslation}
                onValueChange={setShowTranslation}
                trackColor={{ false: colors.surface.separator, true: colors.gold[500] }}
                thumbColor="#FFFFFF"
                accessibilityLabel="Toggle translation display"
              />
            </View>
          </View>
          {showTranslation && (
            <Pressable
              className="flex-row items-center justify-between rounded-xl border border-primary-100 bg-surface-card px-4 py-3 dark:border-primary-800 dark:bg-d-card"
              onPress={() => router.push("/settings/translations")}
              accessibilityRole="button"
              accessibilityLabel="Choose translation"
            >
              <Text className="text-sm text-ink dark:text-d-ink">Choose Translation</Text>
              <Ionicons name="chevron-forward" size={18} color={colors.ink.muted} />
            </Pressable>
          )}
        </View>

        <View className="mb-6">
          <Text className="mb-1 text-base font-semibold text-primary-800 dark:text-primary-200">Recording Mode</Text>
          <Text className="mb-2 text-xs text-gold-600 dark:text-gold-400">Near for phone close to mouth, Mosque for far-field</Text>
          <View className="flex-row rounded-xl border border-primary-100 bg-surface-card p-1 dark:border-primary-800 dark:bg-d-card">
            {GAIN_OPTIONS.map((opt) => {
              const isActive = gainMode === opt.value;
              return (
                <Pressable
                  key={opt.value}
                  className={`flex-1 flex-row items-center justify-center rounded-lg py-2.5 ${isActive ? "bg-primary-500" : ""}`}
                  onPress={() => setGainMode(opt.value)}
                  accessibilityRole="button"
                  accessibilityLabel={`${opt.label} recording mode`}
                  accessibilityState={{ selected: isActive }}
                >
                  <Ionicons
                    name={opt.icon}
                    size={16}
                    color={isActive ? "#FFFFFF" : colors.ink.muted}
                  />
                  <Text
                    className={`ml-1.5 text-sm font-medium ${isActive ? "text-ivory" : "text-ink-muted dark:text-d-ink-muted"}`}
                  >
                    {opt.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        <View className="mb-6">
          <Text className="mb-1 text-base font-semibold text-primary-800 dark:text-primary-200">Server URL</Text>
          <Text className="mb-2 text-xs text-gold-600 dark:text-gold-400">WebSocket endpoint for the recitation server</Text>
          <TextInput
            className="rounded-xl border border-primary-100 bg-surface-card px-4 py-3 text-sm text-ink dark:border-primary-800 dark:bg-d-card dark:text-d-ink"
            value={serverUrl}
            onChangeText={setServerUrl}
            placeholder="ws://localhost:8000/ws/recite"
            placeholderTextColor={colors.ink.muted}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            accessibilityLabel="Server URL input"
          />
        </View>

        <Pressable
          className="mb-8 rounded-xl bg-primary-50 px-4 py-3 dark:bg-primary-950"
          onPress={() => setServerUrl(STREAMING_CONFIG.wsUrl)}
          accessibilityRole="button"
          accessibilityLabel="Reset server URL to default"
        >
          <Text className="text-center text-sm font-medium text-primary-700 dark:text-primary-200">
            Reset to Default
          </Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}
