from app.matching.events import (
    LetterStatus,
    LetterUpdate,
    LetterStatusEvent,
    TajweedUpdate,
    TajweedStatusEvent,
    RecitationErrorDetail,
    RecitationErrorEvent,
    AyahEvent,
    TrackerOutput,
)
from app.matching.recitation_ledger import RecitationLedger


def _letter_event(updates, confidence=0.8):
    return LetterStatusEvent(
        surah_id=1,
        ayah_number=1,
        updates=updates,
        confidence=confidence,
    )


def _tajweed_event():
    return TajweedStatusEvent(
        surah_id=1,
        ayah_number=1,
        updates=[TajweedUpdate(word_index=0, letter_index=0, rule="ghunnah", grade="excellent")],
    )


def _error_event():
    return RecitationErrorEvent(
        surah_id=1,
        ayah_number=1,
        errors=[RecitationErrorDetail(
            error_type="normal",
            speech_error_type="substitution",
            expected_phoneme="s",
            predicted_phoneme="z",
            uthmani_start=0,
            uthmani_end=1,
        )],
    )


def test_new_letter_passes_through():
    ledger = RecitationLedger()
    raw = TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.CORRECT)]),
    ])
    filtered = ledger.apply(raw)
    assert len(filtered.letter_statuses) == 1
    assert filtered.letter_statuses[0].updates[0].status == LetterStatus.CORRECT


def test_correct_is_terminal():
    ledger = RecitationLedger()
    ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.CORRECT)]),
    ]))
    filtered = ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.NOT_SURE)]),
    ]))
    assert len(filtered.letter_statuses) == 0


def test_correct_cannot_downgrade_to_incorrect():
    ledger = RecitationLedger()
    ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.CORRECT)]),
    ]))
    filtered = ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.INCORRECT)]),
    ]))
    assert len(filtered.letter_statuses) == 0


def test_not_sure_upgrades_to_correct():
    ledger = RecitationLedger()
    ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.NOT_SURE)]),
    ]))
    filtered = ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.CORRECT)]),
    ]))
    assert len(filtered.letter_statuses) == 1
    assert filtered.letter_statuses[0].updates[0].status == LetterStatus.CORRECT


def test_not_sure_upgrades_to_incorrect():
    ledger = RecitationLedger()
    ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.NOT_SURE)]),
    ]))
    filtered = ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.INCORRECT)]),
    ]))
    assert len(filtered.letter_statuses) == 1
    assert filtered.letter_statuses[0].updates[0].status == LetterStatus.INCORRECT


def test_incorrect_is_terminal():
    ledger = RecitationLedger()
    ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.INCORRECT)]),
    ]))
    filtered = ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.NOT_SURE)]),
    ]))
    assert len(filtered.letter_statuses) == 0


def test_tajweed_held_until_flush():
    ledger = RecitationLedger()
    raw = TrackerOutput(tajweed_statuses=[_tajweed_event()])
    filtered = ledger.apply(raw)
    assert len(filtered.tajweed_statuses) == 0

    flushed = ledger.flush_deferred()
    assert len(flushed.tajweed_statuses) == 1


def test_errors_held_until_flush():
    ledger = RecitationLedger()
    raw = TrackerOutput(recitation_errors=[_error_event()])
    filtered = ledger.apply(raw)
    assert len(filtered.recitation_errors) == 0

    flushed = ledger.flush_deferred()
    assert len(flushed.recitation_errors) == 1


def test_flush_clears_pending():
    ledger = RecitationLedger()
    ledger.apply(TrackerOutput(
        tajweed_statuses=[_tajweed_event()],
        recitation_errors=[_error_event()],
    ))
    ledger.flush_deferred()
    second_flush = ledger.flush_deferred()
    assert len(second_flush.tajweed_statuses) == 0
    assert len(second_flush.recitation_errors) == 0


def test_ayah_completed_auto_flushes():
    ledger = RecitationLedger()
    raw = TrackerOutput(
        tajweed_statuses=[_tajweed_event()],
        recitation_errors=[_error_event()],
        ayah_events=[AyahEvent(event_type="ayah.completed", surah_id=1, ayah_number=1)],
    )
    filtered = ledger.apply(raw)
    assert len(filtered.tajweed_statuses) == 1
    assert len(filtered.recitation_errors) == 1


def test_reset_clears_all_state():
    ledger = RecitationLedger()
    ledger.apply(TrackerOutput(
        letter_statuses=[_letter_event([LetterUpdate(0, 0, LetterStatus.CORRECT)])],
        tajweed_statuses=[_tajweed_event()],
    ))
    ledger.reset()

    filtered = ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([LetterUpdate(0, 0, LetterStatus.NOT_SURE)]),
    ]))
    assert len(filtered.letter_statuses) == 1

    flushed = ledger.flush_deferred()
    assert len(flushed.tajweed_statuses) == 0


def test_positions_pass_through():
    from app.matching.events import PositionEvent
    ledger = RecitationLedger()
    raw = TrackerOutput(positions=[
        PositionEvent(surah_id=1, ayah_number=1, word_index=3, confidence=0.9),
    ])
    filtered = ledger.apply(raw)
    assert len(filtered.positions) == 1
    assert filtered.positions[0].word_index == 3


def test_mixed_updates_only_upgrades_sent():
    ledger = RecitationLedger()
    ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([
            LetterUpdate(0, 0, LetterStatus.CORRECT),
            LetterUpdate(0, 1, LetterStatus.NOT_SURE),
            LetterUpdate(1, 0, LetterStatus.NOT_SURE),
        ]),
    ]))
    filtered = ledger.apply(TrackerOutput(letter_statuses=[
        _letter_event([
            LetterUpdate(0, 0, LetterStatus.NOT_SURE),
            LetterUpdate(0, 1, LetterStatus.CORRECT),
            LetterUpdate(1, 0, LetterStatus.NOT_SURE),
        ]),
    ]))
    assert len(filtered.letter_statuses) == 1
    updates = filtered.letter_statuses[0].updates
    assert len(updates) == 1
    assert updates[0].word_index == 0
    assert updates[0].letter_index == 1
    assert updates[0].status == LetterStatus.CORRECT
