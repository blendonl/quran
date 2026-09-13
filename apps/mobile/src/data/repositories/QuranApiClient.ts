import { QuranApiError } from "../../domain/errors/QuranApiError";
import { QURAN_API_BASE_URL, QURAN_API_ENDPOINTS, QURAN_API_DEFAULT_PARAMS } from "../../config/apiConfig";

interface ApiResponse<T> {
  chapters?: T;
  chapter?: T;
  verses?: T;
  translations?: T;
  pagination?: {
    per_page: number;
    current_page: number;
    next_page: number | null;
    total_pages: number;
    total_records: number;
  };
}

export class QuranApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = QURAN_API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async fetchChapters(): Promise<ApiResponse<unknown[]>> {
    return this.get(QURAN_API_ENDPOINTS.chapters, {
      language: QURAN_API_DEFAULT_PARAMS.language,
    });
  }

  async fetchChapter(id: number): Promise<ApiResponse<unknown>> {
    return this.get(QURAN_API_ENDPOINTS.chapter(id), {
      language: QURAN_API_DEFAULT_PARAMS.language,
    });
  }

  async fetchVerses(chapterId: number, page = 1, translationId?: number): Promise<ApiResponse<unknown[]>> {
    const params: Record<string, string> = {
      language: QURAN_API_DEFAULT_PARAMS.language,
      words: String(QURAN_API_DEFAULT_PARAMS.words),
      fields: QURAN_API_DEFAULT_PARAMS.fields,
      per_page: String(QURAN_API_DEFAULT_PARAMS.per_page),
      page: String(page),
    };
    if (translationId != null) {
      params.translations = String(translationId);
    }
    return this.get(QURAN_API_ENDPOINTS.verses(chapterId), params);
  }

  async fetchTranslations(): Promise<ApiResponse<unknown[]>> {
    return this.get(QURAN_API_ENDPOINTS.translations, {
      language: QURAN_API_DEFAULT_PARAMS.language,
    });
  }

  private async get<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
    try {
      const url = new URL(`${this.baseUrl}${endpoint}`);
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, value);
        });
      }

      const response = await fetch(url.toString());

      if (!response.ok) {
        throw new QuranApiError(`API request failed: ${response.status} ${response.statusText}`);
      }

      return (await response.json()) as T;
    } catch (error) {
      if (error instanceof QuranApiError) throw error;
      throw new QuranApiError(`Network error: ${error}`);
    }
  }
}
