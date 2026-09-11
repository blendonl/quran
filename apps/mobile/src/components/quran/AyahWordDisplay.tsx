import { Fragment, memo, useEffect, useMemo, useRef } from "react";
import { View, Text, ViewStyle, Animated } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LetterStatusValue } from "../../domain/models/LetterStatus";
import { TajweedGrade, TajweedRule } from "../../domain/models/TajweedStatus";
import { RecitationErrorDetail } from "../../domain/models/RecitationError";
import { WordStatusValue } from "../../domain/models/WordStatus";
import { useSettingsStore } from "../../stores/settingsStore";
import { useThemeColors, ThemeColors, RTL_TEXT, RTL_VIEW, TYPOGRAPHY } from "../../config/themeColors";
import { AyahLetterDisplay, splitIntoDisplayUnits } from "./AyahLetterDisplay";
import { RecitationErrorBanner } from "../recite/RecitationErrorBanner";

interface TajweedEntry {
  rule: TajweedRule;
  grade: TajweedGrade;
}

type CardState = "idle" | "selected" | "current" | "completed";

interface CardStyle {
  className: string;
  nativeStyle?: ViewStyle;
  badgeClassName: string;
}

function createCardStyles(colors: ThemeColors): Record<CardState, CardStyle> {
  return {
    idle: {
      className: "mb-3 rounded-2xl bg-surface-card px-3 py-4 border-r-2 border-gold-100 dark:bg-d-card dark:border-gold-800",
      badgeClassName: "h-8 w-8 items-center justify-center rounded-full bg-gold-50 dark:bg-gold-900",
    },
    selected: {
      className: "mb-3 rounded-2xl px-3 py-4",
      nativeStyle: {
        backgroundColor: colors.gold[50],
        borderWidth: 1.5,
        borderStyle: "dashed",
        borderColor: colors.gold[300],
      },
      badgeClassName: "h-8 w-8 items-center justify-center rounded-full bg-gold-200 dark:bg-gold-700",
    },
    current: {
      className: "mb-3 rounded-2xl px-3 py-4",
      nativeStyle: {
        backgroundColor: colors.surface.bg,
        borderWidth: 1.5,
        borderColor: colors.gold[300],
        shadowColor: colors.gold[500],
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.12,
        shadowRadius: 6,
        elevation: 3,
      },
      badgeClassName: "h-8 w-8 items-center justify-center rounded-full bg-gold-300 dark:bg-gold-600",
    },
    completed: {
      className: "mb-3 rounded-2xl bg-primary-50 px-3 py-4 dark:bg-primary-950",
      badgeClassName: "h-8 w-8 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900",
    },
  };
}

function computeWordErrorIndices(
  text: string,
  words: string[],
  errors: RecitationErrorDetail[],
): Record<number, Set<number>> {
  if (errors.length === 0) return {};

  const errorCharPositions = new Set<number>();
  for (const error of errors) {
    for (let i = error.uthmaniStart; i < error.uthmaniEnd; i++) {
      errorCharPositions.add(i);
    }
  }

  const result: Record<number, Set<number>> = {};
  let charOffset = 0;

  for (let wordIdx = 0; wordIdx < words.length; wordIdx++) {
    const word = words[wordIdx];
    const wordStart = text.indexOf(word, charOffset);
    if (wordStart === -1) continue;

    const units = splitIntoDisplayUnits(word);
    let unitCharOffset = wordStart;
    const errorSet = new Set<number>();

    for (let unitIdx = 0; unitIdx < units.length; unitIdx++) {
      const unit = units[unitIdx];
      for (let c = 0; c < unit.length; c++) {
        if (errorCharPositions.has(unitCharOffset + c)) {
          errorSet.add(unitIdx);
          break;
        }
      }
      unitCharOffset += unit.length;
    }

    if (errorSet.size > 0) {
      result[wordIdx] = errorSet;
    }

    charOffset = wordStart + word.length;
  }

  return result;
}

interface CursorPosition {
  wordIndex: number;
  letterIndex: number;
}

function computeCursorPosition(
  words: string[],
  letterStatuses: Record<number, Record<number, LetterStatusValue>>,
): CursorPosition | null {
  for (let w = 0; w < words.length; w++) {
    const unitCount = splitIntoDisplayUnits(words[w]).length;
    const wordStatuses = letterStatuses[w];
    for (let l = 0; l < unitCount; l++) {
      if (!wordStatuses?.[l]) {
        return { wordIndex: w, letterIndex: l };
      }
    }
  }
  return null;
}

interface WordStatusEntry {
  status: WordStatusValue;
  confidence: number;
  tajweedGrade: string | null;
}

function getWordStatusBackground(
  status: WordStatusValue,
  colors: ThemeColors,
): string | undefined {
  switch (status) {
    case "CORRECT":
      return colors.status.CORRECT + "22";
    case "INCORRECT":
      return colors.status.INCORRECT + "22";
    case "NOT_SURE":
      return colors.status.NOT_SURE + "22";
    default:
      return undefined;
  }
}

interface AyahWordDisplayProps {
  text: string;
  ayahNumber: number;
  letterStatuses: Record<number, Record<number, LetterStatusValue>>;
  tajweedStatuses?: Record<number, Record<number, TajweedEntry>>;
  wordStatuses?: Record<number, WordStatusEntry>;
  recitationErrors?: RecitationErrorDetail[];
  isCompleted: boolean;
  isCurrentAyah: boolean;
  isSelected: boolean;
  translationText?: string;
  recitationMode?: "following" | "learning";
}

export const AyahWordDisplay = memo(function AyahWordDisplay({
  text,
  ayahNumber,
  letterStatuses,
  tajweedStatuses,
  wordStatuses,
  recitationErrors,
  isCompleted,
  isCurrentAyah,
  isSelected,
  translationText,
  recitationMode,
}: AyahWordDisplayProps) {
  const words = useMemo(() => text.split(/\s+/), [text]);
  const fontSize = useSettingsStore((s) => s.fontSize);
  const colors = useThemeColors();

  const isFollowing = recitationMode === "following";

  const wordErrorIndices = useMemo(
    () => (isFollowing || !recitationErrors?.length ? {} : computeWordErrorIndices(text, words, recitationErrors)),
    [isFollowing, text, words, recitationErrors],
  );

  const cursor = useMemo(
    () => (isCurrentAyah && !isCompleted ? computeCursorPosition(words, letterStatuses) : null),
    [isCurrentAyah, isCompleted, words, letterStatuses],
  );

  const cardStyles = useMemo(() => createCardStyles(colors), [colors]);
  const activeWordStyle = useMemo(() => ({ backgroundColor: colors.gold[200] }), [colors]);

  const fadeAnim = useRef(new Animated.Value(1)).current;
  const prevWordIndex = useRef<number | null>(null);

  useEffect(() => {
    if (cursor?.wordIndex === prevWordIndex.current) return;
    prevWordIndex.current = cursor?.wordIndex ?? null;
    fadeAnim.setValue(0.3);
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 120,
      useNativeDriver: true,
    }).start();
  }, [cursor?.wordIndex, fadeAnim]);

  const state: CardState = isCurrentAyah
    ? "current"
    : isSelected
      ? "selected"
      : isCompleted
        ? "completed"
        : "idle";

  const { className: cardClass, nativeStyle: cardStyle, badgeClassName: badgeClass } = cardStyles[state];

  return (
    <View className={cardClass} style={[cardStyle, RTL_VIEW]}>
      <View className="mb-2 flex-row items-center gap-2">
        <View className={badgeClass}>
          {isCompleted ? (
            <Ionicons name="checkmark" size={14} color={colors.primary[500]} />
          ) : (
            <Text className="text-xs font-bold text-gold-500 dark:text-gold-300">{ayahNumber}</Text>
          )}
        </View>
        {isCurrentAyah && !isCompleted && !cursor && (
          <View className="flex-row items-center gap-1">
            <Ionicons name="mic" size={14} color={colors.gold[500]} />
            <Text style={{ fontSize: 12, color: colors.ink.muted }}>Listening...</Text>
          </View>
        )}
      </View>
      <Text
        style={{
          ...RTL_TEXT,
          textAlign: "justify",
          fontSize,
          color: colors.ink.base,
          lineHeight: fontSize * TYPOGRAPHY.ARABIC_LINE_HEIGHT_RATIO,
        }}
      >
        {words.map((word, index) => {
          const isActive = cursor?.wordIndex === index;
          const wordTajweed = isFollowing ? undefined : tajweedStatuses?.[index];
          const wordStatus = isFollowing ? undefined : wordStatuses?.[index];

          let wordStyle = isActive ? activeWordStyle : undefined;
          if (!isActive && wordStatus) {
            const bg = getWordStatusBackground(wordStatus.status, colors);
            if (bg) {
              wordStyle = { backgroundColor: bg };
            }
          }

          const WordWrapper = isActive ? Animated.Text : Text;
          const wrapperStyle = isActive
            ? [wordStyle, { opacity: fadeAnim }]
            : wordStyle
              ? [wordStyle]
              : undefined;

          return (
            <Fragment key={`${ayahNumber}-${index}`}>
              <WordWrapper style={wrapperStyle}>
                <AyahLetterDisplay
                  word={word}
                  letterStatuses={isFollowing ? undefined : letterStatuses[index]}
                  tajweedStatuses={wordTajweed}
                  errorIndices={wordErrorIndices[index]}
                  cursorLetterIndex={isActive ? cursor.letterIndex : undefined}
                />
              </WordWrapper>
              {index < words.length - 1 ? " " : ""}
            </Fragment>
          );
        })}
      </Text>
      {translationText ? (
        <Text
          style={{
            writingDirection: "ltr",
            textAlign: "justify",
            fontSize: Math.max(fontSize * TYPOGRAPHY.TRANSLATION_SCALE, TYPOGRAPHY.MIN_TRANSLATION_SIZE),
            color: colors.ink.secondary,
            lineHeight: Math.max(fontSize * TYPOGRAPHY.TRANSLATION_SCALE, TYPOGRAPHY.MIN_TRANSLATION_SIZE) * 1.6,
            marginTop: 8,
            direction: "ltr",
          }}
        >
          {translationText}
        </Text>
      ) : null}
      {!isFollowing && isCurrentAyah && recitationErrors && recitationErrors.length > 0 && (
        <RecitationErrorBanner errors={recitationErrors} />
      )}
    </View>
  );
});
