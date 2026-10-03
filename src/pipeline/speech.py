"""The only way the tool makes a sound. Enforces CLAUDE.md rule 2 mechanically.

Each utterance names where its text came from. The allowed sources are fixed:

  source               voice    heard by   text comes from
  -------------------  -------  ---------  ------------------------------------------
  bank_answer_noor     noor     Noor       guest_bank.yaml answer_<lang>   (a Line)
  stop_phrase          noor     Noor       stop_phrases.yaml <lang>        (a Line)
  bank_answer_en       guest    guest      guest_bank.yaml answer_en       (a Line)
  guest_question_noor  noor     Noor       machine translation of the guest's own
                                           question: rule 2's one exception, inward
                                           only, spoken to Noor in front of the guest
                                           who asked it, never to the guest

File sources must be a Line marked verified for its language. Anything else raises
Rule2Violation: a bug in routing, never something to recover from.

A Speaker built with allow_unverified=True (the --allow-unverified flag, off by
default) speaks unverified Noor-language lines and logs a warning naming each line's
origin, never its text. It never relaxes bank_answer_en: nothing unverified goes
outward to a guest, in any mode. scripts/check_rule2.py checks all of this.

Machine-made text can only reach Noor's voice, so it can never be spoken to the guest.
Text that is missing or still TODO is refused, not spoken.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from .bank import Line, is_written

SOURCES = {
    "bank_answer_noor": "noor",
    "stop_phrase": "noor",
    "bank_answer_en": "guest",
    "guest_question_noor": "noor",
}
FILE_SOURCES = {"bank_answer_noor", "stop_phrase", "bank_answer_en"}
OUTWARD = {"bank_answer_en"}   # reaches the guest: verified in every mode
log = logging.getLogger(__name__)


class Rule2Violation(RuntimeError):
    """Asked to speak file text that is not verified. Never caught."""


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
        self.voices = voices  # {"noor": Voice, "guest": Voice}
        self.play = play
        self.allow_unverified = allow_unverified

    def say(self, source: str, line) -> Spoken:
        if source not in SOURCES:
            raise ValueError(f"unknown speech source {source!r}")
        voice_key = SOURCES[source]
        if source in FILE_SOURCES:
            if line is None:
                return Spoken(source, voice_key, None, spoken=False, refused="no such phrase")
            if not isinstance(line, Line):
                raise Rule2Violation(f"{source} needs a Line from a bank file, got {type(line).__name__}")
            if not line.verified and (source in OUTWARD or not self.allow_unverified):
                raise Rule2Violation(f"refusing to speak {line.origin}: not verified"
                                     + (" (goes to the guest)" if source in OUTWARD else ""))
            text = line.text
        else:
            text = line
        if not is_written(text):
            return Spoken(source, voice_key, text, spoken=False,
                          refused="not written by a human yet (TODO or missing)")
        unverified = source in FILE_SOURCES and not line.verified
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
