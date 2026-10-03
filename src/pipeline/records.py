"""Exchange records (SPEC-V2.md data model). The only thing Stage 1 persists.

Holds the question text, its translation, the match and the route. No audio, no names,
no guest identifiers. visit_id groups one session's exchanges and nothing else.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def new_visit_id() -> str:
    return uuid.uuid4().hex


def append_exchange(path: Path, *, visit_id, noor_language, raw_transcript_en, translated_noor,
                    matched_entry_id, confidence, route, intent) -> dict:
    record = {
        "id": uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "visit_id": visit_id,
        "noor_language": noor_language,
        "raw_transcript_en": raw_transcript_en,
        "translated_noor": translated_noor,
        "matched_entry_id": matched_entry_id,
        "confidence": None if confidence is None else round(confidence, 4),
        "route": route,
        "intent": intent,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
