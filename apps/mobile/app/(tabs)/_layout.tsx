import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";

import { useColorScheme } from "@/components/useColorScheme";

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: "#2f9568",
        tabBarInactiveTintColor: colorScheme === "dark" ? "#888" : "#999",
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Recite",
          tabBarIcon: ({ color, size }) => <Ionicons name="mic" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="quran"
        options={{
          title: "Quran",
          tabBarIcon: ({ color, size }) => <Ionicons name="book" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: "Settings",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="settings-outline" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
