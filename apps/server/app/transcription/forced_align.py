import logging
import math
from dataclasses import dataclass

import torch

logger = logging.getLogger(__name__)

FRAME_STRIDE_SAMPLES = 320


@dataclass
class WordBoundary:
    word_index: int
    start_frame: int
    end_frame: int
    score: float
    start_sample: int
    end_sample: int


@dataclass
class ForcedAlignResult:
    word_boundaries: list[WordBoundary]
    total_frames: int


def text_to_tokens(text: str, vocab: dict[str, int]) -> list[int]:
    tokens = []
    for ch in text:
        if ch in vocab:
            tokens.append(vocab[ch])
    return tokens


def build_word_token_ranges(
    words: list[str], vocab: dict[str, int]
) -> list[tuple[int, int, int]]:
    ranges = []
    token_offset = 0
    for word_index, word in enumerate(words):
        word_tokens = text_to_tokens(word, vocab)
        if word_tokens:
            ranges.append((word_index, token_offset, token_offset + len(word_tokens)))
        token_offset += len(word_tokens)
    return ranges


def run_forced_align(
    log_probs: torch.Tensor,
    tokens: list[int],
    blank_id: int = 0,
) -> tuple[torch.Tensor, torch.Tensor]:
    import torchaudio

    targets = torch.tensor([tokens], dtype=torch.int32)
    input_lengths = torch.tensor([log_probs.size(0)])
    target_lengths = torch.tensor([len(tokens)])

    aligned_tokens, scores = torchaudio.functional.forced_align(
        log_probs.unsqueeze(0),
        targets,
        input_lengths,
        target_lengths,
        blank_id,
    )
    return aligned_tokens.squeeze(0), scores.squeeze(0)


def extract_word_boundaries(
    aligned_tokens: torch.Tensor,
    scores: torch.Tensor,
    word_token_ranges: list[tuple[int, int, int]],
    blank_id: int = 0,
    frame_stride: int = FRAME_STRIDE_SAMPLES,
) -> list[WordBoundary]:
    token_frames: dict[int, list[int]] = {}
    token_scores: dict[int, list[float]] = {}

    current_token_idx = -1
    for frame_idx in range(aligned_tokens.size(0)):
        token_val = aligned_tokens[frame_idx].item()
        if token_val == blank_id:
            continue

        if token_val != blank_id:
            if current_token_idx < 0:
                current_token_idx = 0
            elif (
                frame_idx > 0
                and aligned_tokens[frame_idx - 1].item() != token_val
            ):
                current_token_idx += 1

        if current_token_idx not in token_frames:
            token_frames[current_token_idx] = []
            token_scores[current_token_idx] = []
        token_frames[current_token_idx].append(frame_idx)
        token_scores[current_token_idx].append(scores[frame_idx].item())

    boundaries = []
    for word_index, tok_start, tok_end in word_token_ranges:
        word_frames = []
        word_scores = []
        for ti in range(tok_start, tok_end):
            word_frames.extend(token_frames.get(ti, []))
            word_scores.extend(token_scores.get(ti, []))

        if not word_frames:
            continue

        start_frame = min(word_frames)
        end_frame = max(word_frames)
        avg_log_prob = sum(word_scores) / len(word_scores)
        score = math.exp(avg_log_prob)

        boundaries.append(WordBoundary(
            word_index=word_index,
            start_frame=start_frame,
            end_frame=end_frame,
            score=score,
            start_sample=start_frame * frame_stride,
            end_sample=end_frame * frame_stride,
        ))

    return boundaries
