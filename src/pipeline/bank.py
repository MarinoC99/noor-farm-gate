"""Loads the human-written banks. Unfinished or unverified content fails safe, never open.

Every sentence the tool may speak is loaded as a Line that carries its `verified` flag.
The Speaker refuses, with an exception, to voice a Line whose source is not verified
(CLAUDE.md rule 2). An entry auto-answers only if its commitment flag is literally
`false` and it is `verified: true`.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

INTENTS = ("money", "general", "logistics", "safety")


def is_written(value) -> bool:
    return isinstance(value, str) and bool(value.strip()) and "TODO" not in value


@dataclass(frozen=True)
class Line:
    """One sentence the tool may say, and whether a human verified its source."""
    text: Optional[str]   # None if missing or TODO
    verified: bool        # True only if the source says literally `verified: true`
    origin: str           # e.g. "guest_bank.yaml:parking.answer_en"


@dataclass(frozen=True)
class Entry:
    id: str
    intent: Optional[str]        # None unless one of INTENTS
    commitment_flag: object      # raw value from the file; only `False` means "not a commitment"
    paraphrases: tuple           # written paraphrases only
    answer_en: Line
    answer_sw: Line
    verified: bool

    @property
    def is_commitment(self) -> bool:
        return self.commitment_flag is not False

    @property
    def answerable(self) -> bool:
        return (not self.is_commitment and self.verified
                and self.answer_en.text is not None and self.answer_sw.text is not None)


def _line(value, verified, origin) -> Line:
    return Line(value if is_written(value) else None, verified, origin)


def load_guest_bank(path: Path) -> list:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    items = raw["entries"] if isinstance(raw, dict) else raw
    entries, seen = [], set()
    for item in items:
        entry_id = item.get("id")
        if not is_written(entry_id):
            raise ValueError(f"{path.name}: every entry needs a written id")
        if entry_id in seen:
            raise ValueError(f"{path.name}: duplicate id {entry_id!r}")
        seen.add(entry_id)
        verified = item.get("verified") is True
        intent = item.get("intent")
        entry = Entry(
            id=entry_id,
            intent=intent if intent in INTENTS else None,
            commitment_flag=item.get("commitment"),
            paraphrases=tuple(p for p in item.get("paraphrases_en") or [] if is_written(p)),
            answer_en=_line(item.get("answer_en"), verified, f"{path.name}:{entry_id}.answer_en"),
            answer_sw=_line(item.get("answer_sw"), verified, f"{path.name}:{entry_id}.answer_sw"),
            verified=verified,
        )
        if verified and (entry.answer_en.text is None or entry.answer_sw.text is None):
            raise ValueError(f"{path.name}: {entry_id} is verified: true but an answer is missing or TODO")
        entries.append(entry)
    return entries


class StopPhrases:
    """config/stop_phrases.yaml. Keys: no_match, money, date, safety, default."""

    def __init__(self, path: Path):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self.lines = {
            key: _line((node or {}).get("sw"), (node or {}).get("verified") is True,
                       f"{path.name}:{key}.sw")
            for key, node in (raw.get("phrases") or {}).items()
        }

    def resolve(self, stop_key: str):
        """"no_match" or "commitment.<reason>" -> (file key, Line or None).

        A commitment whose reason has no phrase of its own (logistics, general, or an
        unclassified entry) uses `default`, as the file's routing notes say.
        """
        if stop_key == "no_match":
            key = "no_match"
        else:
            reason = stop_key.split(".", 1)[1]
            key = reason if reason in self.lines and reason not in ("no_match", "default") \
                else "default"
        return key, self.lines.get(key)
