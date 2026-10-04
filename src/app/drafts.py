"""Stage 3: the drafting queue. Noor answers an unanswered question; it waits for review.

A draft is a PENDING entry, bank-shaped, kept in records/pending_entries.json (git-
ignored: it holds real guest wording). It is never written into guest_bank.yaml, so the
matcher and the Speaker never load it, and its verified flags start false, so the
Speaker's guard would refuse it anyway. No exception to either is added here.

- paraphrases_en come only from transcripts guests actually said that came back
  NO_MATCH or WEAK_MATCH: the bank learns the words guests really used. Anything else
  is rejected.
- answer_<lang> is what Noor typed. answer_en is left empty; nothing generates it.
- Review (her daughter, at weekends) adds the English, the commitment flag and the
  intent, and ticks verified per language. A reviewed draft is still not in the bank
  and still cannot be spoken; adding it to the bank is a separate, human step.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.pipeline.bank import INTENTS, Entry, Line, is_written

MAX_ANSWER_CHARS = 400


class QueueUnreadable(ValueError):
    """records/pending_entries.json is not a list of drafts (hand-edited, or truncated)."""


def load(path: Path) -> list:
    if not path.exists():
        return []
    try:
        drafts = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise QueueUnreadable(f"{path.name} is not valid JSON: {e}") from None
    if not isinstance(drafts, list) or not all(
            isinstance(d, dict) and isinstance(d.get("id"), str)
            and isinstance(d.get("paraphrases_en"), list) and isinstance(d.get("verified"), dict)
            for d in drafts):
        raise QueueUnreadable(f"{path.name} is not a list of drafts")
    return drafts


def save(path: Path, drafts: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(drafts, ensure_ascii=False, indent=1) + "\n")
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def _strings(value, what) -> list:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"{what} must be a list of strings")
    return value


def gap_transcripts(records: list) -> dict:
    """Exact transcripts that came back NO_MATCH / WEAK_MATCH -> True if every record with
    that transcript is test data."""
    seen = {}
    for r in records:
        if r["route"] in ("NO_MATCH", "WEAK_MATCH"):
            t = r["raw_transcript_en"].strip()
            seen[t] = seen.get(t, True) and r.get("test_data") is True
    return seen


def new_draft(*, paraphrases: list, answer_noor: str, lang: str, records: list) -> dict:
    """A pending entry. Raises ValueError if a paraphrase is not a real failed transcript."""
    gaps = gap_transcripts(records)
    paraphrases = list(dict.fromkeys(p.strip() for p in _strings(paraphrases, "paraphrases") if p.strip()))
    if not isinstance(answer_noor, str):
        raise ValueError("the answer must be text")
    if not paraphrases:
        raise ValueError("a draft needs at least one guest question")
    unknown = [p for p in paraphrases if p not in gaps]
    if unknown:
        raise ValueError(f"not questions guests actually asked without an answer: {unknown}")
    answer = (answer_noor or "").strip()
    if not is_written(answer):
        raise ValueError("the answer is empty")
    if len(answer) > MAX_ANSWER_CHARS:
        raise ValueError(f"the answer is longer than {MAX_ANSWER_CHARS} characters")
    return {
        "id": "pending-" + uuid.uuid4().hex[:10],
        "status": "pending",
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "intent": None,
        "commitment": None,          # unknown: treated as a commitment if it were ever loaded
        "paraphrases_en": paraphrases,
        "answer_en": "",             # left empty: written by a person at review, never generated
        f"answer_{lang}": answer,
        "verified": {lang: False, "en": False},
        "test_data": all(gaps[p] for p in paraphrases),
    }


def language_of(draft: dict) -> Optional[str]:
    """The Noor language a draft was written in: its one verified key other than en."""
    return next((k for k in (draft.get("verified") or {}) if k != "en"), None)


def review(draft: dict, *, answer_en: str, commitment: Optional[bool], intent: Optional[str],
           verified: dict, paraphrases: Optional[list] = None) -> dict:
    """The weekend review: the English, the flags, and who checked what. Still pending in
    the sense that matters: it is not in the bank and cannot be spoken.

    paraphrases, if given, can only remove guest wordings, never add one: the summary's
    grouping by meaning is approximate and can put a different question in the group."""
    if answer_en is not None and not isinstance(answer_en, str):
        raise ValueError("the English answer must be text")
    if not isinstance(verified, dict):
        raise ValueError("verified must be an object of language: true/false")
    answer_en = (answer_en or "").strip()
    if len(answer_en) > MAX_ANSWER_CHARS:
        raise ValueError(f"the English answer is longer than {MAX_ANSWER_CHARS} characters")
    if paraphrases is not None:
        keep = {p.strip() for p in _strings(paraphrases, "paraphrases")}
        kept = [p for p in draft["paraphrases_en"] if p in keep]
        if not kept:
            raise ValueError("keep at least one guest question")
        draft["paraphrases_en"] = kept
    draft["answer_en"] = answer_en
    draft["commitment"] = commitment if isinstance(commitment, bool) else None
    draft["intent"] = intent if intent in INTENTS else None
    for lang in list(draft["verified"]):
        flag = verified.get(lang) is True
        text = answer_en if lang == "en" else draft.get(f"answer_{lang}", "")
        draft["verified"][lang] = flag and is_written(text)   # cannot verify an empty answer
    draft["status"] = "reviewed" if all(draft["verified"].values()) else "pending"
    draft["reviewed"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return draft


def as_entry(draft: dict, lang: str) -> Entry:
    """The draft in the shape the Speaker and router use, for the rule-2 check."""
    v = draft.get("verified") or {}
    return Entry(
        id=draft["id"],
        intent=draft.get("intent") if draft.get("intent") in INTENTS else None,
        commitment_flag=draft.get("commitment"),
        paraphrases=tuple(draft.get("paraphrases_en") or ()),
        answer_en=Line(draft.get("answer_en") if is_written(draft.get("answer_en")) else None,
                       v.get("en") is True, f"pending_entries.json:{draft['id']}.answer_en"),
        answer_noor=Line(draft.get(f"answer_{lang}") if is_written(draft.get(f"answer_{lang}")) else None,
                         v.get(lang) is True, f"pending_entries.json:{draft['id']}.answer_{lang}"),
        noor_language=lang,
    )
