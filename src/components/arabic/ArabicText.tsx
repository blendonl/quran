import { Text, TextProps } from "react-native";

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
      className={`font-arabic leading-loose text-gray-900 ${sizeClasses[size]} ${className}`}
      style={{ writingDirection: "rtl", textAlign: "right" }}
      {...props}
    >
      {text}
    </Text>
  );
}
