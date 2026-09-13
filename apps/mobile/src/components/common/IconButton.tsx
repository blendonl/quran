import { Pressable, PressableProps } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useThemeColors } from "../../config/themeColors";

interface IconButtonProps extends Omit<PressableProps, "children"> {
  icon: keyof typeof Ionicons.glyphMap;
  size?: number;
  color?: string;
}

export function IconButton({
  icon,
  size = 24,
  color,
  ...pressableProps
}: IconButtonProps) {
  const colors = useThemeColors();

  return (
    <Pressable
      className="items-center justify-center rounded-full p-2"
      accessibilityRole="button"
      {...pressableProps}
    >
      <Ionicons name={icon} size={size} color={color ?? colors.ink.base} />
    </Pressable>
  );
}
