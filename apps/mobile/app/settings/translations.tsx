import { useEffect, useMemo, useState, useCallback } from "react";
import { View, Text, Pressable, TextInput, SectionList } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useThemeColors } from "@src/config/themeColors";
import { useTranslations } from "@src/hooks/useTranslations";
import { useSettingsStore } from "@src/stores/settingsStore";
import { Translation } from "@src/domain/models/Translation";
import { LoadingSpinner } from "@src/components/common/LoadingSpinner";
import { ErrorDisplay } from "@src/components/common/ErrorDisplay";

interface TranslationSection {
  title: string;
  data: Translation[];
}

export default function TranslationPickerScreen() {
  const router = useRouter();
  const colors = useThemeColors();
  const { translations, isLoading, error, loadTranslations } = useTranslations();
  const translationId = useSettingsStore((s) => s.translationId);
  const setTranslationId = useSettingsStore((s) => s.setTranslationId);
  const [search, setSearch] = useState("");

  useEffect(() => {
    loadTranslations();
  }, [loadTranslations]);

  const sections = useMemo(() => {
    const filtered = search
      ? translations.filter(
          (t) =>
            t.name.toLowerCase().includes(search.toLowerCase()) ||
            t.authorName.toLowerCase().includes(search.toLowerCase()) ||
            t.languageName.toLowerCase().includes(search.toLowerCase()),
        )
      : translations;

    const grouped = new Map<string, Translation[]>();
    for (const t of filtered) {
      const lang = t.languageName;
      if (!grouped.has(lang)) grouped.set(lang, []);
      grouped.get(lang)!.push(t);
    }

    const result: TranslationSection[] = [];
    for (const [title, data] of grouped) {
      result.push({ title, data });
    }
    return result.sort((a, b) => a.title.localeCompare(b.title));
  }, [translations, search]);

  const handleSelect = useCallback(
    (id: number) => {
      setTranslationId(id);
      router.back();
    },
    [setTranslationId, router],
  );

  const renderItem = useCallback(
    ({ item }: { item: Translation }) => {
      const isSelected = item.id === translationId;
      return (
        <Pressable
          className="flex-row items-center border-b border-surface-sep px-4 py-3 dark:border-d-sep"
          onPress={() => handleSelect(item.id)}
        >
          <View className="flex-1">
            <Text className="text-sm font-medium text-ink dark:text-d-ink">{item.name}</Text>
            <Text className="mt-0.5 text-xs text-ink-muted dark:text-d-ink-muted">{item.authorName}</Text>
          </View>
          {isSelected && <Ionicons name="checkmark-circle" size={22} color={colors.gold[500]} />}
        </Pressable>
      );
    },
    [translationId, handleSelect, colors],
  );

  const renderSectionHeader = useCallback(
    ({ section }: { section: TranslationSection }) => (
      <View className="bg-surface-elevated px-4 py-2 dark:bg-d-elevated">
        <Text className="text-xs font-semibold uppercase text-ink-muted dark:text-d-ink-muted">{section.title}</Text>
      </View>
    ),
    [],
  );

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 bg-ivory dark:bg-d-bg">
        <LoadingSpinner />
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView className="flex-1 bg-ivory dark:bg-d-bg">
        <ErrorDisplay message={error} onRetry={loadTranslations} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-ivory dark:bg-d-bg">
      <View className="flex-row items-center border-b border-surface-sep px-4 py-3 dark:border-d-sep">
        <Pressable onPress={() => router.back()} className="mr-3">
          <Ionicons name="arrow-back" size={22} color={colors.ink.base} />
        </Pressable>
        <Text className="text-lg font-bold text-ink dark:text-d-ink">Translations</Text>
      </View>

      <View className="border-b border-surface-sep px-4 py-2 dark:border-d-sep">
        <TextInput
          className="rounded-lg bg-surface-elevated px-3 py-2 text-sm text-ink dark:bg-d-elevated dark:text-d-ink"
          placeholder="Search translations..."
          placeholderTextColor={colors.ink.muted}
          value={search}
          onChangeText={setSearch}
          autoCapitalize="none"
          autoCorrect={false}
        />
      </View>

      <SectionList
        sections={sections}
        renderItem={renderItem}
        renderSectionHeader={renderSectionHeader}
        keyExtractor={(item) => String(item.id)}
        stickySectionHeadersEnabled
      />
    </SafeAreaView>
  );
}
