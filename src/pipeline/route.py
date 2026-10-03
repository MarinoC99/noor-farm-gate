"""Matching and the branch decision. No model here decides what is said: it only picks
which human-written entry, or which stop, applies."""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

from .bank import Entry, is_written

BANK, NOOR_BANK = "BANK", "NOOR_BANK"
WEAK_MATCH, NO_MATCH, COMMITMENT = "WEAK_MATCH", "NO_MATCH", "COMMITMENT"


@dataclass
class Match:
    entry: Entry
    score: float
    paraphrase: str  # the entry's closest paraphrase


class Matcher:
    def __init__(self, embedder, entries):
        self.embedder = embedder
        self.rows = [(e, p) for e in entries for p in e.paraphrases]
        self.vectors = embedder.embed([p for _, p in self.rows]) if self.rows else np.zeros((0, 0))

    def rank(self, question_en: str) -> list:
        """Every entry with at least one written paraphrase, best first."""
        if not self.rows:
            return []
        scores = self.vectors @ self.embedder.embed([question_en])[0]
        best = {}
        for (entry, paraphrase), score in zip(self.rows, scores):
            if entry.id not in best or score > best[entry.id].score:
                best[entry.id] = Match(entry, float(score), paraphrase)
        return sorted(best.values(), key=lambda m: m.score, reverse=True)


class Triggers:
    """config/commitment_triggers.yaml: words that make any question a commitment."""

    def __init__(self, path: Path):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self.groups = []  # [(heading, [(term, pattern), ...])], in file order
        for heading, terms in raw.items():
            compiled = []
            for term in terms or []:
                term = str(term).strip().lower()
                if not is_written(term):
                    continue
                if not any(ch.isalnum() for ch in term):  # "$", "€": match anywhere
                    pattern = re.compile(re.escape(term))
                else:
                    words = r"\s+".join(re.escape(w) for w in term.split())
                    pattern = re.compile(rf"(?<!\w){words}(?!\w)", re.IGNORECASE)
                compiled.append((term, pattern))
            self.groups.append((heading, compiled))

    def find(self, text: str) -> list:
        """[(heading, term), ...] for every term present, headings in file order."""
        return [(heading, term) for heading, terms in self.groups
                for term, pattern in terms if pattern.search(text)]


@dataclass
class Decision:
    route: str
    reason: str
    match: Optional[Match]          # the entry the decision is about, if any
    intent: Optional[str]           # recorded intent; None unless an entry was matched
    stop_phrase_key: Optional[str]  # "no_match" or "commitment.<reason>"


def decide(ranking: list, threshold: float, trigger_hits=(), weak_floor=None,
           allow_unverified=False) -> Decision:
    """allow_unverified (off by default) lets a written but unverified answer reach BANK;
    the Speaker must be built with the same setting to speak it."""
    top = ranking[0] if ranking else None
    strong = top if top is not None and top.score >= threshold else None

    if trigger_hits:
        heading = trigger_hits[0][0]
        words = ", ".join(dict.fromkeys(term for _, term in trigger_hits))
        return Decision(COMMITMENT, f"trigger words in transcript: {words}; reason {heading}",
                        strong, strong.entry.intent if strong else None,
                        f"commitment.{heading}")
    if top is None:
        return Decision(NO_MATCH, "no entry has a written paraphrase", None, None, "no_match")
    if top.score < threshold:
        if weak_floor is None:
            return Decision(NO_MATCH, f"best score {top.score:.3f} < threshold {threshold}; "
                            "weak_match_floor not set, so weak and none are not split",
                            None, None, "no_match")
        if top.score >= weak_floor:
            return Decision(WEAK_MATCH, f"best score {top.score:.3f} in "
                            f"[floor {weak_floor}, threshold {threshold})",
                            top, None, "no_match")
        return Decision(NO_MATCH, f"best score {top.score:.3f} < floor {weak_floor}",
                        None, None, "no_match")
    entry = top.entry
    if entry.is_commitment:
        why = entry.intent or "unclassified"
        flag = "commitment: true" if entry.commitment_flag is True \
            else f"commitment flag not set to false ({entry.commitment_flag!r})"
        return Decision(COMMITMENT, f"{flag}; reason {why}", top, entry.intent,
                        f"commitment.{why}")
    if not (entry.answerable or (allow_unverified and entry.has_answers)):
        return Decision(NO_MATCH, "matched entry has no verified answer (verified: false)",
                        top, entry.intent, "no_match")
    return Decision(BANK, f"score {top.score:.3f} >= threshold {threshold}, not a commitment, "
                    "no trigger words" + ("" if entry.verified else "; UNVERIFIED answer"),
                    top, entry.intent, None)
