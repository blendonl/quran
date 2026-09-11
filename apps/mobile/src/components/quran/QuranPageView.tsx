import { useCallback, useEffect, useMemo, useRef } from "react";
import { Text, View } from "react-native";
import { FlashList } from "@shopify/flash-list";
import { Ayah } from "../../domain/models/Ayah";
import { useRecitationStore } from "../../stores/recitationStore";
import { useSettingsStore } from "../../stores/settingsStore";
import { useThemeColors, RTL_TEXT } from "../../config/themeColors";
import { AyahItem } from "./AyahItem";
import { AyahSkeletonList } from "./AyahSkeleton";

const BISMILLAH_TEXT = "\u0628\u0650\u0633\u0652\u0645\u0650 \u0627\u0644\u0644\u0651\u064E\u0647\u0650 \u0627\u0644\u0631\u0651\u064E\u062D\u0652\u0645\u064E\u0640\u0670\u0646\u0650 \u0627\u0644\u0631\u0651\u064E\u062D\u0650\u064A\u0645\u0650";

interface QuranPageViewProps {
  ayahs: Ayah[];
  isLoading: boolean;
  bismillahPre: boolean;
  onAyahPress: (verseNumber: number) => void;
  initialScrollToAyah?: number;
}

function BismillahHeader() {
  const fontSize = useSettingsStore((s) => s.fontSize);
  const colors = useThemeColors();

  return (
    <View className="mb-4 items-center px-3 py-3">
      <View className="mb-2 h-px w-16 bg-gold-200 dark:bg-gold-700" />
      <Text
        style={{ fontSize, color: colors.gold[500], ...RTL_TEXT }}
      >
        {BISMILLAH_TEXT}
      </Text>
      <View className="mt-2 h-px w-16 bg-gold-200 dark:bg-gold-700" />
    </View>
  );
}

export function QuranPageView({ ayahs, isLoading, bismillahPre, onAyahPress, initialScrollToAyah }: QuranPageViewProps) {
  const listRef = useRef<FlashList<Ayah>>(null);

  const fontSize = useSettingsStore((s) => s.fontSize);
  const showTranslation = useSettingsStore((s) => s.showTranslation);
  const currentAyahNumber = useRecitationStore((s) => s.currentAyahNumber);

  const initialIndex = useMemo(() => {
    if (initialScrollToAyah == null || ayahs.length === 0) return undefined;
    const idx = ayahs.findIndex((a) => a.verseNumber === initialScrollToAyah);
    return idx >= 0 ? idx : undefined;
  }, [initialScrollToAyah, ayahs]);

  // During streaming, scroll to the current ayah (small jumps — animated is fine)
  useEffect(() => {
    if (currentAyahNumber == null || ayahs.length === 0) return;
    const index = ayahs.findIndex((a) => a.verseNumber === currentAyahNumber);
    if (index < 0) return;
    listRef.current?.scrollToIndex({ index, animated: true });
  }, [currentAyahNumber, ayahs]);

  const renderItem = useCallback(
    ({ item }: { item: Ayah }) => (
      <AyahItem
        textUthmani={item.textUthmani}
        verseNumber={item.verseNumber}
        translationText={item.translation}
        onPress={onAyahPress}
      />
    ),
    [onAyahPress],
  );

  const keyExtractor = useCallback((item: Ayah) => String(item.id), []);

  const header = useMemo(
    () => (bismillahPre ? <BismillahHeader /> : null),
    [bismillahPre],
  );

  if (isLoading) {
    return <AyahSkeletonList />;
  }

  return (
    <View className="flex-1 bg-ivory px-2 pt-3 dark:bg-d-bg">
      <FlashList
        key={`${fontSize}-${showTranslation}`}
        ref={listRef}
        data={ayahs}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        initialScrollIndex={initialIndex}
        estimatedItemSize={200}
        ListHeaderComponent={header}
        ListFooterComponent={<View style={{ height: 112 }} />}
      />
    </View>
  );
}
