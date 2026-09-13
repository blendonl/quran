export const QURAN_API_BASE_URL = "https://api.quran.com/api/v4";

export const QURAN_API_ENDPOINTS = {
  chapters: "/chapters",
  chapter: (id: number) => `/chapters/${id}`,
  verses: (chapterId: number) => `/verses/by_chapter/${chapterId}`,
  verse: (verseKey: string) => `/verses/by_key/${verseKey}`,
  translations: "/resources/translations",
} as const;

export const DEFAULT_TRANSLATION_ID = 20;

export const QURAN_API_DEFAULT_PARAMS = {
  language: "en",
  words: false,
  fields: "text_uthmani,text_imlaei",
  per_page: 300,
} as const;
