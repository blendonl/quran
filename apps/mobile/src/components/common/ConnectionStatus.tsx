import { View, Text } from "react-native";
import { useSettingsStore } from "../../stores/settingsStore";

type Status = "disconnected" | "connecting" | "connected" | "error";

const STATUS_CONFIG: Record<Status, { color: string; label: string } | null> = {
  disconnected: null,
  connecting: { color: "bg-yellow-400", label: "Connecting" },
  connected: { color: "bg-green-500", label: "Connected" },
  error: { color: "bg-red-500", label: "Error" },
};

interface ConnectionStatusProps {
  status: Status;
}

export function ConnectionStatus({ status }: ConnectionStatusProps) {
  const config = STATUS_CONFIG[status];
  const serverUrl = useSettingsStore((s) => s.serverUrl);
  if (!config) return null;

  return (
    <View className="flex-row items-center">
      <View className={`h-2 w-2 rounded-full ${config.color}`} />
      <Text className="ml-1.5 text-xs text-ink-muted dark:text-d-ink-muted">
        {config.label}: {serverUrl}
      </Text>
    </View>
  );
}
