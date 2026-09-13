import { memo, useMemo } from "react";
import { View, Text } from "react-native";
import { RecitationErrorDetail } from "../../domain/models/RecitationError";
import { useThemeColors } from "../../config/themeColors";

const MAX_DISPLAYED_ERRORS = 3;

function describeError(error: RecitationErrorDetail): string {
  const { speechErrorType, expectedPhoneme, predictedPhoneme, tajweedRule } = error;

  if (tajweedRule) {
    return `Tajweed (${tajweedRule}): expected ${expectedPhoneme}`;
  }

  switch (speechErrorType) {
    case "delete":
      return `Missing: ${expectedPhoneme}`;
    case "insert":
      return `Extra sound: ${predictedPhoneme}`;
    default:
      return `Wrong letter: expected ${expectedPhoneme}`;
  }
}

interface RecitationErrorBannerProps {
  errors: RecitationErrorDetail[];
}

export const RecitationErrorBanner = memo(function RecitationErrorBanner({
  errors,
}: RecitationErrorBannerProps) {
  const colors = useThemeColors();

  const descriptions = useMemo(() => {
    const seen = new Set<string>();
    const unique: string[] = [];
    for (const e of errors) {
      const desc = describeError(e);
      if (!seen.has(desc)) {
        seen.add(desc);
        unique.push(desc);
      }
    }
    return unique;
  }, [errors]);

  if (descriptions.length === 0) return null;

  const displayed = descriptions.slice(0, MAX_DISPLAYED_ERRORS);
  const remaining = descriptions.length - displayed.length;

  return (
    <View
      style={{
        backgroundColor: colors.status.INCORRECT + "12",
        borderLeftWidth: 3,
        borderLeftColor: colors.status.INCORRECT,
        borderRadius: 8,
        paddingHorizontal: 12,
        paddingVertical: 8,
        marginTop: 6,
      }}
    >
      {displayed.map((desc, i) => (
        <Text
          key={i}
          style={{
            color: colors.status.INCORRECT,
            fontSize: 13,
            lineHeight: 18,
          }}
        >
          {desc}
        </Text>
      ))}
      {remaining > 0 && (
        <Text
          style={{
            color: colors.ink.muted,
            fontSize: 12,
            marginTop: 2,
          }}
        >
          and {remaining} more
        </Text>
      )}
    </View>
  );
});
