import { View, Text, TextInput, Pressable, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useSettingsStore } from "@src/stores/settingsStore";
import { STREAMING_CONFIG } from "@src/config/streamingConfig";

export default function SettingsModal() {
  const { serverUrl, setServerUrl } = useSettingsStore();
  const router = useRouter();

  return (
    <SafeAreaView className="flex-1 bg-ivory">
      <View className="flex-row items-center justify-between px-5 pb-3 pt-2">
        <Text
          className="text-2xl text-primary-500"
          style={{ fontFamily: "Amiri" }}
        >
          Settings
        </Text>
        <Pressable
          className="h-9 w-9 items-center justify-center rounded-full"
          onPress={() => router.back()}
        >
          <Ionicons name="close" size={22} color="#1B5E3B" />
        </Pressable>
      </View>

      <ScrollView className="flex-1 px-5 pt-4">
        <View className="mb-6">
          <Text className="mb-1 text-base font-semibold text-primary-800">
            Server URL
          </Text>
          <Text className="mb-2 text-xs text-gold-600">
            WebSocket endpoint for the recitation server
          </Text>
          <TextInput
            className="rounded-xl border border-primary-100 bg-white px-4 py-3 text-sm text-gray-900"
            value={serverUrl}
            onChangeText={setServerUrl}
            placeholder="ws://localhost:8000/ws/recite"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
          />
        </View>

        <Pressable
          className="rounded-xl bg-primary-50 px-4 py-3"
          onPress={() => setServerUrl(STREAMING_CONFIG.wsUrl)}
        >
          <Text className="text-center text-sm font-medium text-primary-700">
            Reset to Default
          </Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}
