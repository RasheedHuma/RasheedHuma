"""Speaker-aware transcript segmentation utilities.

Segments are built from complete speaker turns. Normal segments do not exceed
1,500 words. If a single detected speaker turn exceeds 1,500 words, that turn
is kept intact so speaker turns remain strict boundaries.
"""

from __future__ import annotations

import re
from typing import List


SPEAKER_PATTERN = re.compile(
    r"""
    (?=
        (?:^|\n)
        [ \t]*
        (?:
            [A-Z][A-Z.'’\-]+
            (?:[ \t]+[A-Z][A-Z.'’\-]+)*
            |
            UNIDENTIFIED[ \t]+(?:MALE|FEMALE|PERSON|SPEAKER)
        )
        (?:,[^:\n]{1,100})?
        :
    )
    """,
    flags=re.MULTILINE | re.VERBOSE,
)


def word_count(text: str) -> int:
    """Return a simple whitespace-token word count."""
    return len(str(text).split())


def split_into_speaker_turns(text: str) -> List[str]:
    """Split transcript text into complete speaker turns.

    Material appearing before the first detected speaker label, such as a
    commercial-break or video-clip marker, is attached to the first turn.
    If no speaker labels are detected, the entire text is returned as one turn.
    """
    if text is None or not str(text).strip():
        return []

    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    starts = [match.start() for match in SPEAKER_PATTERN.finditer(normalized)]

    if not starts:
        return [normalized]

    turns: List[str] = []
    prefix = normalized[: starts[0]].strip()

    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(normalized)
        turn = normalized[start:end].strip()

        if index == 0 and prefix:
            turn = f"{prefix}\n{turn}"

        if turn:
            turns.append(turn)

    return turns


def segment_by_speaker(text: str, max_words: int = 1500) -> List[str]:
    """Combine complete speaker turns into segments.

    Rules:
    - Every normal segment begins at a speaker-turn boundary.
    - Speaker turns are never divided.
    - A turn is added only when the resulting segment stays at or below
      ``max_words``.
    - If one speaker turn alone exceeds ``max_words``, it is retained intact as
      an oversized segment.
    """
    if max_words <= 0:
        raise ValueError("max_words must be greater than zero")

    turns = split_into_speaker_turns(text)
    if not turns:
        return []

    segments: List[str] = []
    current_turns: List[str] = []
    current_words = 0

    for turn in turns:
        turn_words = word_count(turn)

        # A single oversized speaker turn remains intact.
        if turn_words > max_words:
            if current_turns:
                segments.append("\n".join(current_turns).strip())
                current_turns = []
                current_words = 0

            segments.append(turn.strip())
            continue

        # Close the current segment before adding a turn that would exceed the
        # normal maximum. The new segment therefore starts with this speaker.
        if current_turns and current_words + turn_words > max_words:
            segments.append("\n".join(current_turns).strip())
            current_turns = [turn]
            current_words = turn_words
        else:
            current_turns.append(turn)
            current_words += turn_words

    if current_turns:
        segments.append("\n".join(current_turns).strip())

    return segments
