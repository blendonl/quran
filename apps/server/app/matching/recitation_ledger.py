import logging

from app.matching.events import (
    LetterStatus,
    LetterUpdate,
    LetterStatusEvent,
    TajweedStatusEvent,
    RecitationErrorEvent,
    TrackerOutput,
)

logger = logging.getLogger(__name__)

MONOTONIC_UPGRADE: dict[LetterStatus, set[LetterStatus]] = {
    LetterStatus.NOT_SURE: {LetterStatus.CORRECT, LetterStatus.INCORRECT},
    LetterStatus.INCORRECT: set(),
    LetterStatus.CORRECT: set(),
}


class RecitationLedger:
    def __init__(self):
        self._committed: dict[tuple[int, int], LetterStatus] = {}
        self._pending_tajweed: list[TajweedStatusEvent] = []
        self._pending_errors: list[RecitationErrorEvent] = []

    def reset(self):
        self._committed.clear()
        self._pending_tajweed.clear()
        self._pending_errors.clear()

    def apply(self, raw: TrackerOutput) -> TrackerOutput:
        filtered = TrackerOutput(
            positions=raw.positions,
            ayah_events=raw.ayah_events,
            mistakes=raw.mistakes,
            surah_completed=raw.surah_completed,
            word_statuses=raw.word_statuses,
            locating_timeout=raw.locating_timeout,
        )

        for event in raw.letter_statuses:
            upgrades = self._apply_letter_event(event)
            if upgrades:
                filtered.letter_statuses.append(LetterStatusEvent(
                    surah_id=event.surah_id,
                    ayah_number=event.ayah_number,
                    updates=upgrades,
                    confidence=event.confidence,
                ))

        self._pending_tajweed.extend(raw.tajweed_statuses)
        self._pending_errors.extend(raw.recitation_errors)

        for ayah_event in raw.ayah_events:
            if ayah_event.event_type == "ayah.completed":
                flushed = self._flush()
                filtered.tajweed_statuses.extend(flushed.tajweed_statuses)
                filtered.recitation_errors.extend(flushed.recitation_errors)

        return filtered

    def flush_deferred(self) -> TrackerOutput:
        return self._flush()

    def _flush(self) -> TrackerOutput:
        out = TrackerOutput(
            tajweed_statuses=list(self._pending_tajweed),
            recitation_errors=list(self._pending_errors),
        )
        self._pending_tajweed.clear()
        self._pending_errors.clear()
        return out

    def _apply_letter_event(self, event: LetterStatusEvent) -> list[LetterUpdate]:
        upgrades: list[LetterUpdate] = []
        for update in event.updates:
            key = (update.word_index, update.letter_index)
            current = self._committed.get(key)
            if current is None:
                self._committed[key] = update.status
                upgrades.append(update)
            elif update.status in MONOTONIC_UPGRADE[current]:
                self._committed[key] = update.status
                upgrades.append(update)
        return upgrades
