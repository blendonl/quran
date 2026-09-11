import type { WebSocketClient } from "./WebSocketClient";
import type { PositionUpdate } from "../../domain/models/PositionUpdate";
import type {
  LetterStatusValue,
  LetterStatusUpdate,
} from "../../domain/models/LetterStatus";
import type { TajweedGradeUpdate } from "../../domain/models/TajweedStatus";
import type { RecitationErrorUpdate } from "../../domain/models/RecitationError";
import type { WordStatusUpdate } from "../../domain/models/WordStatus";

interface StoreActions {
  updatePosition: (u: PositionUpdate) => void;
  applyLetterStatuses: (u: LetterStatusUpdate) => void;
  applyTajweedStatuses: (u: TajweedGradeUpdate) => void;
  applyRecitationErrors: (u: RecitationErrorUpdate) => void;
  applyWordStatuses: (u: WordStatusUpdate) => void;
  clearLetterStatusesForAyah: (n: number) => void;
  markAyahCompleted: (n: number) => void;
}

const TERMINAL_STATUSES = new Set<LetterStatusValue>(["CORRECT", "INCORRECT"]);

const STATUS_RANK: Record<LetterStatusValue, number> = {
  INCORRECT: 0,
  NOT_SURE: 1,
  CORRECT: 2,
};

export class RecitationUpdateFilter {
  private lastWordIndexByAyah: Record<number, number> = {};
  private committedLetters: Record<
    number,
    Record<number, Record<number, LetterStatusValue>>
  > = {};
  private pendingTajweed: Record<number, TajweedGradeUpdate[]> = {};
  private pendingErrors: Record<number, RecitationErrorUpdate> = {};

  bind(client: WebSocketClient, getStore: () => StoreActions): void {
    client.onPositionUpdate = (update) => {
      const last = this.lastWordIndexByAyah[update.ayahNumber] ?? -1;
      const isNewAyah = !(update.ayahNumber in this.lastWordIndexByAyah);
      if (!isNewAyah && update.wordIndex < last) return;
      this.lastWordIndexByAyah[update.ayahNumber] = update.wordIndex;
      getStore().updatePosition(update);
    };

    client.onLetterStatusUpdate = (update) => {
      if (update.confidence === 0) return;
      const ayahCommitted = this.committedLetters[update.ayahNumber] ?? {};
      const filtered = update.updates.filter((u) => {
        const existing = ayahCommitted[u.wordIndex]?.[u.letterIndex];
        if (!existing) return true;
        if (TERMINAL_STATUSES.has(existing)) return false;
        return STATUS_RANK[u.status] > STATUS_RANK[existing];
      });
      if (filtered.length === 0) return;

      for (const u of filtered) {
        if (!ayahCommitted[u.wordIndex]) ayahCommitted[u.wordIndex] = {};
        ayahCommitted[u.wordIndex][u.letterIndex] = u.status;
      }
      this.committedLetters[update.ayahNumber] = ayahCommitted;

      getStore().applyLetterStatuses({ ...update, updates: filtered });
    };

    client.onTajweedStatusUpdate = (update) => {
      if (!this.pendingTajweed[update.ayahNumber]) {
        this.pendingTajweed[update.ayahNumber] = [];
      }
      this.pendingTajweed[update.ayahNumber].push(update);
    };

    client.onRecitationError = (update) => {
      const pending = this.pendingErrors[update.ayahNumber];
      if (!pending) {
        this.pendingErrors[update.ayahNumber] = { ...update };
        return;
      }
      const seen = new Set(
        pending.errors.map(
          (e) => `${e.uthmaniStart}:${e.uthmaniEnd}:${e.expectedPhoneme}`,
        ),
      );
      for (const e of update.errors) {
        const key = `${e.uthmaniStart}:${e.uthmaniEnd}:${e.expectedPhoneme}`;
        if (!seen.has(key)) {
          seen.add(key);
          pending.errors.push(e);
        }
      }
    };

    client.onWordStatusUpdate = (update) => {
      getStore().applyWordStatuses(update);
    };

    client.onAyahStarted = (surahId, ayahNumber) => {
      delete this.lastWordIndexByAyah[ayahNumber];
      delete this.committedLetters[ayahNumber];
      delete this.pendingTajweed[ayahNumber];
      delete this.pendingErrors[ayahNumber];
      const store = getStore();
      store.clearLetterStatusesForAyah(ayahNumber);
      store.updatePosition({
        surahId,
        ayahNumber,
        wordIndex: 0,
        confidence: 0,
      });
      this.lastWordIndexByAyah[ayahNumber] = 0;
    };

    client.onAyahCompleted = (_surahId, ayahNumber) => {
      this.flushDeferredUpdates(ayahNumber, getStore);
      getStore().markAyahCompleted(ayahNumber);
    };
  }

  flushDeferredUpdates(
    ayahNumber: number,
    getStore: () => StoreActions,
  ): void {
    const store = getStore();
    const tajweedList = this.pendingTajweed[ayahNumber];
    if (tajweedList) {
      for (const update of tajweedList) {
        store.applyTajweedStatuses(update);
      }
      delete this.pendingTajweed[ayahNumber];
    }
    const errorUpdate = this.pendingErrors[ayahNumber];
    if (errorUpdate && errorUpdate.errors.length > 0) {
      store.applyRecitationErrors(errorUpdate);
      delete this.pendingErrors[ayahNumber];
    }
  }

  reset(): void {
    this.lastWordIndexByAyah = {};
    this.committedLetters = {};
    this.pendingTajweed = {};
    this.pendingErrors = {};
  }
}

export const recitationUpdateFilter = new RecitationUpdateFilter();
