"""Stage 3: the summary. Reads records/exchanges.jsonl, counts, returns the counts.

Offline: a local file in, numbers out. It generates no advice and recommends nothing;
it shows what guests asked and what happened, and Noor decides.

Unanswered questions are grouped by meaning with the same MiniLM model and the same
match threshold the tool already uses to match questions, so "asked the same thing"
means here what it means everywhere else in the tool.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml

from src.pipeline.bank import is_written

GAP_ROUTES = ("NO_MATCH", "WEAK_MATCH")


def load_records(path: Path) -> list:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_labels(path: Path, code: str) -> dict:
    raw = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("labels") or {}
    out, missing = {}, 0
    for key, node in raw.items():
        text = (node or {}).get(code)
        if is_written(text):
            out[key] = text
        else:
            out[key] = (node or {}).get("en", key)
            missing += 1
    return {"labels": out, "untranslated": missing}


def _norm(text: str) -> str:
    return " ".join(text.lower().strip().strip("?.!,").split())


def _group_by_meaning(transcripts, embedder, threshold):
    """[(wording, count)] -> groups, most asked first. Each group's representative is
    its most frequent wording; a wording joins the first group it scores >= threshold
    against."""
    wordings = Counter()
    first = {}
    for t in transcripts:
        n = _norm(t)
        wordings[n] += 1
        first.setdefault(n, t.strip())
    ordered = [n for n, _ in sorted(wordings.items(), key=lambda kv: (-kv[1], kv[0]))]
    if not ordered:
        return []
    vecs = embedder.embed([first[n] for n in ordered])
    groups = []  # [{"rep": n, "vec": v, "members": [n, ...]}]
    for n, v in zip(ordered, vecs):
        best, best_score = None, -1.0
        for g in groups:
            s = float(g["vec"] @ v)
            if s > best_score:
                best, best_score = g, s
        if best is not None and best_score >= threshold:
            best["members"].append(n)
        else:
            groups.append({"rep": n, "vec": v, "members": [n]})
    out = []
    for g in groups:
        out.append({
            "question_en": first[g["rep"]],
            "count": sum(wordings[m] for m in g["members"]),
            "variants": [{"wording": first[m], "count": wordings[m]} for m in g["members"][1:]],
            "members": g["members"],
        })
    return sorted(out, key=lambda g: -g["count"])


def summarize(records, *, embedder, translate, triggers, threshold) -> dict:
    routes = Counter(r["route"] for r in records)
    known_no_answer = sum(1 for r in records if r["route"] == "NO_MATCH" and r.get("matched_entry_id"))

    # Why commitments stopped: a trigger word in the question, else the matched entry's intent.
    def commit_reason(r):
        hits = triggers.find(r["raw_transcript_en"])
        return hits[0][0] if hits else (r.get("intent") or "unknown")

    commitments = [r for r in records if r["route"] == "COMMITMENT"]
    reasons = Counter(commit_reason(r) for r in commitments)

    # The gap: everything that came back NO_MATCH or WEAK_MATCH, grouped by what was asked.
    gap_records = [r for r in records if r["route"] in GAP_ROUTES]
    groups = _group_by_meaning([r["raw_transcript_en"] for r in gap_records], embedder, threshold)
    by_norm = defaultdict(list)
    for r in gap_records:
        by_norm[_norm(r["raw_transcript_en"])].append(r)
    cache = {}

    def noor(text):
        if text not in cache:
            cache[text] = translate(text)
        return cache[text]

    gaps = []
    for g in groups:
        members = [r for n in g["members"] for r in by_norm[n]]
        nearest = Counter(r.get("matched_entry_id") for r in members if r.get("matched_entry_id"))
        gaps.append({
            "question_en": g["question_en"],
            "question_noor": noor(g["question_en"]),
            "count": g["count"],
            "variants": g["variants"],
            "routes": dict(Counter(r["route"] for r in members)),
            "known_entry": nearest.most_common(1)[0][0] if nearest else None,
            "test_records": sum(1 for r in members if r.get("test_data") is True),
        })

    # Which commitment stops recur: by matched entry, or by trigger reason if none matched.
    by_entry = defaultdict(list)
    for r in commitments:
        by_entry[r.get("matched_entry_id") or f"(trigger: {commit_reason(r)})"].append(r)
    commit_entries = []
    for key, rs in sorted(by_entry.items(), key=lambda kv: -len(kv[1])):
        rep = Counter(r["raw_transcript_en"].strip() for r in rs).most_common(1)[0][0]
        commit_entries.append({
            "entry": key, "count": len(rs), "reason": Counter(commit_reason(r) for r in rs).most_common(1)[0][0],
            "question_en": rep, "question_noor": noor(rep),
        })

    return {
        "records": len(records),
        "test_records": sum(1 for r in records if r.get("test_data") is True),
        "visits": len({r.get("visit_id") for r in records}),
        "outcomes": {
            "answered": routes.get("BANK", 0),
            "handed_back": routes.get("NOOR_BANK", 0),
            "stopped_commitment": routes.get("COMMITMENT", 0),
            "stopped_known": known_no_answer,
            "stopped_weak": routes.get("WEAK_MATCH", 0),
            "stopped_unknown": routes.get("NO_MATCH", 0) - known_no_answer,
        },
        "commitment_reasons": dict(reasons.most_common()),
        "intents": dict(Counter(r.get("intent") or "none" for r in records).most_common()),
        "gaps": gaps,
        "commitment_entries": commit_entries,
        "grouping_threshold": threshold,
    }
