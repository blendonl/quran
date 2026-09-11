import { Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Tabs, useRouter } from "expo-router";
import { useThemeColors } from "@src/config/themeColors";

function SettingsButton() {
  const colors = useThemeColors();
  const router = useRouter();

  return (
    <Pressable onPress={() => router.push("/settings")} className="mr-3" accessibilityLabel="Settings">
      <Ionicons name="settings-outline" size={22} color={colors.ink.muted} />
    </Pressable>
  );
}

export default function TabLayout() {
  const colors = useThemeColors();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary[500],
        tabBarInactiveTintColor: colors.ink.muted,
        tabBarStyle: {
          backgroundColor: colors.surface.bg,
          borderTopColor: colors.surface.separator,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Recite",
          tabBarAccessibilityLabel: "Recite tab",
          tabBarIcon: ({ color, size }) => <Ionicons name="mic" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="quran"
        options={{
          title: "Quran",
          tabBarAccessibilityLabel: "Quran tab",
          tabBarIcon: ({ color, size }) => <Ionicons name="book" size={size} color={color} />,
        }}
      />
    </Tabs>
  );
}
