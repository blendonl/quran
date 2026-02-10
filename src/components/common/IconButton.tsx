import { Pressable, PressableProps } from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface IconButtonProps extends Omit<PressableProps, "children"> {
  icon: keyof typeof Ionicons.glyphMap;
  size?: number;
  color?: string;
}

export function IconButton({
  icon,
  size = 24,
  color = "#333",
  ...pressableProps
}: IconButtonProps) {
  return (
    <Pressable
      className="items-center justify-center rounded-full p-2"
      {...pressableProps}
    >
      <Ionicons name={icon} size={size} color={color} />
    </Pressable>
  );
}
