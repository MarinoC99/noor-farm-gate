"""The only way the tool makes a sound. Enforces CLAUDE.md rule 2 mechanically.

Each utterance names where its text came from. The allowed sources are fixed:

  source               voice      heard by   text comes from
  -------------------  ---------  ---------  ----------------------------------------
  bank_answer_sw       Swahili    Noor       guest_bank.yaml answer_sw   (a Line)
  bank_answer_en       English    guest      guest_bank.yaml answer_en   (a Line)
  stop_phrase          Swahili    Noor       stop_phrases.yaml           (a Line)
  guest_question_sw    Swahili    Noor       machine translation of the guest's own
                                             question: the single exception in rule 2,
                                             spoken to Noor and never to the guest

Bank and stop sources must be a Line whose source is `verified: true`. Anything else
raises Rule2Violation: that is a bug in routing, never something to recover from.
The one exception is a Speaker built with allow_unverified=True (the terminal app's
--allow-unverified flag, off by default): it speaks unverified lines and logs a warning
naming each line's origin, never its text. scripts/check_rule2.py never sets it.
Machine-made text can only ever reach the Swahili voice, so it can never be spoken to
the guest. Text that is missing or still TODO is refused, not spoken.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from .bank import Line, is_written

SOURCES = {
    "bank_answer_sw": "sw",
    "bank_answer_en": "en",
    "stop_phrase": "sw",
    "guest_question_sw": "sw",
}
HUMAN_SOURCES = {"bank_answer_sw", "bank_answer_en", "stop_phrase"}
log = logging.getLogger(__name__)


class Rule2Violation(RuntimeError):
    """Asked to speak human-bank text that is not verified. Never caught."""


@dataclass
class Spoken:
    source: str
    voice: str
    text: Optional[str]
    spoken: bool
    seconds: float = 0.0
    refused: Optional[str] = None
    unverified: bool = False      # spoken under allow_unverified


class Speaker:
    def __init__(self, voices: dict, play: bool = True, allow_unverified: bool = False):
        self.voices = voices  # {"sw": Voice, "en": Voice}
        self.play = play
        self.allow_unverified = allow_unverified

    def say(self, source: str, line) -> Spoken:
        if source not in SOURCES:
            raise ValueError(f"unknown speech source {source!r}")
        voice_key = SOURCES[source]
        if source in HUMAN_SOURCES:
            if line is None:
                return Spoken(source, voice_key, None, spoken=False, refused="no such phrase")
            if not isinstance(line, Line):
                raise Rule2Violation(f"{source} needs a Line from a bank file, got {type(line).__name__}")
            if not line.verified and not self.allow_unverified:
                raise Rule2Violation(f"refusing to speak {line.origin}: its source is verified: false")
            text = line.text
        else:
            text = line
        if not is_written(text):
            return Spoken(source, voice_key, text, spoken=False,
                          refused="not written by a human yet (TODO or missing)")
        unverified = source in HUMAN_SOURCES and not line.verified
        if unverified:
            log.warning("speaking UNVERIFIED %s (--allow-unverified)", line.origin)
        voice = self.voices[voice_key]
        audio = voice.synthesize(text)
        seconds = len(audio) / voice.sample_rate
        if self.play:
            import sounddevice as sd
            sd.play(audio, voice.sample_rate)
            sd.wait()
        return Spoken(source, voice_key, text, spoken=self.play, seconds=seconds,
                      refused=None if self.play else "muted (--mute)", unverified=unverified)
