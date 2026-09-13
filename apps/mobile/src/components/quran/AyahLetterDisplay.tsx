import { memo, useMemo } from "react";
import { Text } from "react-native";
import { LetterStatusValue } from "../../domain/models/LetterStatus";
import { TajweedGrade, TajweedRule } from "../../domain/models/TajweedStatus";
import { useThemeColors } from "../../config/themeColors";

const TASHKEEL_REGEX = /[\u0640\u064B-\u065E\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7-\u06E8\u06EA-\u06ED]/;

interface TajweedEntry {
  rule: TajweedRule;
  grade: TajweedGrade;
}

interface AyahLetterDisplayProps {
  word: string;
  letterStatuses?: Record<number, LetterStatusValue>;
  tajweedStatuses?: Record<number, TajweedEntry>;
  errorIndices?: Set<number>;
  cursorLetterIndex?: number;
}

export function splitIntoDisplayUnits(word: string): string[] {
  const units: string[] = [];
  let current = "";

  for (const ch of word) {
    if (TASHKEEL_REGEX.test(ch)) {
      current += ch;
    } else {
      if (current) {
        units.push(current);
      }
      current = ch;
    }
  }
  if (current) {
    units.push(current);
  }

  return units;
}

export const AyahLetterDisplay = memo(function AyahLetterDisplay({
  word,
  letterStatuses,
  tajweedStatuses,
  errorIndices,
  cursorLetterIndex,
}: AyahLetterDisplayProps) {
  const colors = useThemeColors();

  const hasStatuses =
    cursorLetterIndex != null ||
    (letterStatuses && Object.keys(letterStatuses).length > 0) ||
    (tajweedStatuses && Object.keys(tajweedStatuses).length > 0) ||
    (errorIndices && errorIndices.size > 0);

  const units = useMemo(
    () => (hasStatuses ? splitIntoDisplayUnits(word) : null),
    [word, hasStatuses],
  );

  if (!units) {
    return <Text>{word}</Text>;
  }

  return (
    <Text>
      {units.map((unit, idx) => {
        const status = letterStatuses?.[idx];
        const isCursor = idx === cursorLetterIndex;
        const color = status ? colors.status[status] : colors.ink.base;
        const tajweed = tajweedStatuses?.[idx];
        const hasError = errorIndices?.has(idx);
        const underlineColor = hasError
          ? colors.status.INCORRECT
          : tajweed
            ? colors.tajweed[tajweed.grade]
            : undefined;
        const underlineStyle = hasError ? "dashed" : "solid";

        return (
          <Text
            key={idx}
            style={{
              color,
              textDecorationLine: underlineColor ? "underline" : "none",
              textDecorationColor: underlineColor,
              textDecorationStyle: underlineStyle,
              backgroundColor: isCursor ? colors.gold[100] : undefined,
              fontWeight: isCursor ? "bold" : undefined,
            }}
          >
            {unit}
          </Text>
        );
      })}
    </Text>
  );
});
