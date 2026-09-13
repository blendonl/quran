import { memo, useCallback } from "react";
import { Pressable } from "react-native";
import { useRecitationStore } from "../../stores/recitationStore";
import { LetterStatusValue } from "../../domain/models/LetterStatus";
import { TajweedGrade, TajweedRule } from "../../domain/models/TajweedStatus";
import { RecitationErrorDetail } from "../../domain/models/RecitationError";
import { WordStatusValue } from "../../domain/models/WordStatus";
import { AyahWordDisplay } from "./AyahWordDisplay";

const EMPTY_LETTER_STATUSES: Record<number, Record<number, LetterStatusValue>> =
  {};

interface TajweedEntry {
  rule: TajweedRule;
  grade: TajweedGrade;
}

const EMPTY_TAJWEED_STATUSES: Record<number, Record<number, TajweedEntry>> = {};
const EMPTY_RECITATION_ERRORS: RecitationErrorDetail[] = [];

interface WordStatusEntry {
  status: WordStatusValue;
  confidence: number;
  tajweedGrade: string | null;
}
const EMPTY_WORD_STATUSES: Record<number, WordStatusEntry> = {};

interface AyahItemProps {
  textUthmani: string;
  verseNumber: number;
  translationText?: string;
  onPress: (verseNumber: number) => void;
}

export const AyahItem = memo(function AyahItem({
  textUthmani,
  verseNumber,
  translationText,
  onPress,
}: AyahItemProps) {
  const currentAyahNumber = useRecitationStore((s) => s.currentAyahNumber);
  const selectedAyahNumber = useRecitationStore((s) => s.selectedAyahNumber);
  const isCompleted = useRecitationStore(
    (s) => s.completedAyahs[verseNumber] === true,
  );
  const ayahLetterStatuses = useRecitationStore(
    (s) => s.letterStatuses[verseNumber] ?? EMPTY_LETTER_STATUSES,
  );
  const ayahTajweedStatuses = useRecitationStore(
    (s) => s.tajweedStatuses[verseNumber] ?? EMPTY_TAJWEED_STATUSES,
  );
  const ayahRecitationErrors = useRecitationStore(
    (s) => s.recitationErrors[verseNumber] ?? EMPTY_RECITATION_ERRORS,
  );
  const ayahWordStatuses = useRecitationStore(
    (s) => s.wordStatuses[verseNumber] ?? EMPTY_WORD_STATUSES,
  );
  const recitationMode = useRecitationStore((s) => s.recitationMode);

  const isCurrentAyah = currentAyahNumber === verseNumber;
  const isSelected = selectedAyahNumber === verseNumber;

  const handlePress = useCallback(() => {
    onPress(verseNumber);
  }, [onPress, verseNumber]);

  return (
    <Pressable
      onPress={handlePress}
      style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}
      accessibilityRole="button"
      accessibilityLabel={`Ayah ${verseNumber}`}
    >
      <AyahWordDisplay
        text={textUthmani}
        ayahNumber={verseNumber}
        letterStatuses={ayahLetterStatuses}
        tajweedStatuses={ayahTajweedStatuses}
        wordStatuses={ayahWordStatuses}
        recitationErrors={ayahRecitationErrors}
        isCompleted={isCompleted}
        isCurrentAyah={isCurrentAyah}
        isSelected={isSelected}
        translationText={translationText}
        recitationMode={recitationMode}
      />
    </Pressable>
  );
});
