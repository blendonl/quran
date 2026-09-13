export interface Surah {
  id: number;
  revelationPlace: string;
  revelationOrder: number;
  bismillahPre: boolean;
  nameSimple: string;
  nameComplex: string;
  nameArabic: string;
  versesCount: number;
  pages: number[];
  translatedName: {
    languageName: string;
    name: string;
  };
}
