"""Loads the human-written banks for one Noor language. Unfinished or unverified
content fails safe, never open.

Every sentence the tool may speak from the files is loaded as a Line that carries its
`verified` flag. Verification is per language (`verified: {en: ..., es: ..., sw: ...}`):
`en` covers the answer spoken to the guest, the Noor-language flag covers what Noor
hears. The Speaker refuses, with an exception, to voice an unverified Line (CLAUDE.md
rule 2). An entry auto-answers only if its commitment flag is literally `false` and
both its English and its Noor-language answer are verified.
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
    """One sentence the tool may say, and whether a speaker of its language verified it."""
    text: Optional[str]   # None if missing or TODO
    verified: bool        # True only if the file says literally `true` for this language
    origin: str           # e.g. "guest_bank.yaml:parking.answer_es"


@dataclass(frozen=True)
class Entry:
    id: str
    intent: Optional[str]        # None unless one of INTENTS
    commitment_flag: object      # raw value from the file; only `False` means "not a commitment"
    paraphrases: tuple           # written paraphrases only
    answer_en: Line              # spoken to the guest
    answer_noor: Line            # read to Noor, in her language
    noor_language: str

    @property
    def is_commitment(self) -> bool:
        return self.commitment_flag is not False

    @property
    def has_answers(self) -> bool:
        """Not a commitment and both answers written. Says nothing about verification."""
        return (not self.is_commitment
                and self.answer_en.text is not None and self.answer_noor.text is not None)

    @property
    def verified(self) -> bool:
        return self.answer_en.verified and self.answer_noor.verified

    @property
    def answerable(self) -> bool:
        return self.has_answers and self.verified


def _line(value, verified, origin) -> Line:
    return Line(value if is_written(value) else None, verified, origin)


def _verified_map(node, where) -> dict:
    if not isinstance(node, dict):
        raise ValueError(f"{where}: `verified` must be a per-language map, e.g. "
                         "{en: false, es: false, sw: false}")
    return {lang: flag is True for lang, flag in node.items()}


def load_guest_bank(path: Path, noor_language: str) -> list:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    items = raw["entries"] if isinstance(raw, dict) else raw
    entries, seen = [], set()
    field = f"answer_{noor_language}"
    for item in items:
        entry_id = item.get("id")
        if not is_written(entry_id):
            raise ValueError(f"{path.name}: every entry needs a written id")
        if entry_id in seen:
            raise ValueError(f"{path.name}: duplicate id {entry_id!r}")
        seen.add(entry_id)
        verified = _verified_map(item.get("verified"), f"{path.name}:{entry_id}")
        intent = item.get("intent")
        entry = Entry(
            id=entry_id,
            intent=intent if intent in INTENTS else None,
            commitment_flag=item.get("commitment"),
            paraphrases=tuple(p for p in item.get("paraphrases_en") or [] if is_written(p)),
            answer_en=_line(item.get("answer_en"), verified.get("en", False),
                            f"{path.name}:{entry_id}.answer_en"),
            answer_noor=_line(item.get(field), verified.get(noor_language, False),
                              f"{path.name}:{entry_id}.{field}"),
            noor_language=noor_language,
        )
        for line in (entry.answer_en, entry.answer_noor):
            if line.verified and line.text is None:
                raise ValueError(f"{line.origin} is marked verified but is missing or TODO")
        entries.append(entry)
    return entries


class StopPhrases:
    """config/stop_phrases.yaml for one Noor language. Keys: no_match, money, date,
    safety, default. `en` in the file is a gloss and is never spoken."""

    def __init__(self, path: Path, noor_language: str):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        phrases = raw.get("phrases") or {}
        self.lines, self.gloss_en = {}, {}
        for key, node in phrases.items():
            node = node or {}
            verified = _verified_map(node.get("verified"), f"{path.name}:{key}")
            line = _line(node.get(noor_language), verified.get(noor_language, False),
                         f"{path.name}:{key}.{noor_language}")
            if line.verified and line.text is None:
                raise ValueError(f"{line.origin} is marked verified but is missing or TODO")
            self.lines[key] = line
            self.gloss_en[key] = node.get("en")

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
