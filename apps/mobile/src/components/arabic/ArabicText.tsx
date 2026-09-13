import { Text, TextProps } from "react-native";
import { RTL_TEXT } from "../../config/themeColors";

interface ArabicTextProps extends TextProps {
  text: string;
  size?: "sm" | "md" | "lg" | "xl" | "2xl";
}

const sizeClasses: Record<string, string> = {
  sm: "text-lg",
  md: "text-2xl",
  lg: "text-3xl",
  xl: "text-4xl",
  "2xl": "text-5xl",
};

export function ArabicText({ text, size = "lg", className = "", ...props }: ArabicTextProps) {
  return (
    <Text
      className={`font-arabic leading-loose text-ink dark:text-d-ink ${sizeClasses[size]} ${className}`}
      style={{ ...RTL_TEXT, textAlign: "right" }}
      {...props}
    >
      {text}
    </Text>
  );
}
