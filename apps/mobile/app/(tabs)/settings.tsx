import { View, Text, Pressable, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Slider from "@react-native-community/slider";
import { useSettingsStore } from "@src/stores/settingsStore";
import { DEFAULT_ELONGATION_SETTINGS } from "@src/config/elongationConfig";

export default function SettingsScreen() {
  const { elongationSettings, setElongationSettings, modelStatus } = useSettingsStore();

  return (
    <SafeAreaView className="flex-1 bg-white" edges={["bottom"]}>
      <ScrollView className="flex-1 px-4 pt-4">
        <Text className="mb-6 text-lg font-bold text-gray-900">Settings</Text>

        <View className="mb-6">
          <Text className="mb-1 text-base font-semibold text-gray-800">Model Status</Text>
          <View className="rounded-lg bg-gray-50 p-3">
            <Text className="text-sm text-gray-600">
              {modelStatus === "ready"
                ? "Speech model loaded and ready"
                : modelStatus === "downloading"
                  ? "Downloading speech model..."
                  : modelStatus === "error"
                    ? "Error loading model"
                    : "Model not downloaded"}
            </Text>
          </View>
        </View>

        <View className="mb-6">
          <Text className="mb-3 text-base font-semibold text-gray-800">
            Elongation Detection
          </Text>

          <SettingSlider
            label="Threshold"
            value={elongationSettings.thresholdMs}
            minimumValue={100}
            maximumValue={500}
            step={10}
            unit="ms"
            onValueChange={(v) => setElongationSettings({ thresholdMs: v })}
          />

          <SettingSlider
            label="Base Unit"
            value={elongationSettings.baseUnitMs}
            minimumValue={50}
            maximumValue={300}
            step={10}
            unit="ms"
            onValueChange={(v) => setElongationSettings({ baseUnitMs: v })}
          />

          <SettingSlider
            label="Max Repetitions"
            value={elongationSettings.maxRepetitions}
            minimumValue={2}
            maximumValue={15}
            step={1}
            unit=""
            onValueChange={(v) => setElongationSettings({ maxRepetitions: v })}
          />
        </View>

        <Pressable
          className="rounded-lg bg-gray-100 px-4 py-3"
          onPress={() => setElongationSettings(DEFAULT_ELONGATION_SETTINGS)}
        >
          <Text className="text-center text-sm font-medium text-gray-700">
            Reset to Defaults
          </Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

interface SettingSliderProps {
  label: string;
  value: number;
  minimumValue: number;
  maximumValue: number;
  step: number;
  unit: string;
  onValueChange: (value: number) => void;
}

function SettingSlider({
  label,
  value,
  minimumValue,
  maximumValue,
  step,
  unit,
  onValueChange,
}: SettingSliderProps) {
  return (
    <View className="mb-4">
      <View className="mb-1 flex-row items-center justify-between">
        <Text className="text-sm text-gray-600">{label}</Text>
        <Text className="text-sm font-medium text-primary-700">
          {Math.round(value)}
          {unit}
        </Text>
      </View>
      <Slider
        minimumValue={minimumValue}
        maximumValue={maximumValue}
        step={step}
        value={value}
        onValueChange={onValueChange}
        minimumTrackTintColor="#2f9568"
        maximumTrackTintColor="#e5e7eb"
        thumbTintColor="#2f9568"
      />
    </View>
  );
}
