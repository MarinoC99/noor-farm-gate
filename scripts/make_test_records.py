"""Write synthetic exchange records so the summary has something to show.

Every record is marked "test_data": true and carries a "source" note, so test data can
always be told apart from real exchanges. Re-running replaces earlier test records and
never touches real ones.

The questions are typed English test questions written for this script (not real
guests, not ASR output). Everything after that is the real pipeline: the translator,
the matcher, the commitment triggers and the routing, run on today's bank. So which
questions are answered, weak, unmatched or stopped is the tool's own decision, not
chosen here. One exchange is recorded as NOOR_BANK to show Noor answering herself.

Usage: .venv/bin/python scripts/make_test_records.py
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline import language  # noqa: E402
from src.pipeline.bank import load_guest_bank  # noqa: E402
from src.pipeline.models import Embedder, Translator  # noqa: E402
from src.pipeline.route import BANK, NOOR_BANK, Matcher, Triggers, decide  # noqa: E402

RECORDS = ROOT / "records" / "exchanges.jsonl"
SOURCE = "synthetic test question, typed (not ASR); routed by the real pipeline"
HANDED_BACK = "is there a bench to sit on"   # recorded as Noor choosing to answer herself

# (date, questions) per visit.
VISITS = [
    ("2026-09-12", ["where can I park the car", "how much is the tour", "is there wifi here", "can I take photos"]),
    ("2026-09-13", ["do you use pesticides", "what does your coffee taste like", "can we see where you roast it", "do you have wifi"]),
    ("2026-09-15", ["is there a toilet", "how long does the tour take", "how high are we", "do you speak English"]),
    ("2026-09-17", ["can I buy some beans to take home", "how big is your farm", "can I connect to the internet", "is the walk steep"]),
    ("2026-09-19", ["are you part of a cooperative", "what kind of coffee is this", "is there a cafe nearby", "can my kids come"]),
    ("2026-09-20", ["where does your water come from", "when is the harvest", "can we drink a coffee here", "what should I wear"]),
    ("2026-09-22", ["how much is a bag of coffee", "what does the coffee taste like", "is there anywhere to buy souvenirs", "where can I park"]),
    ("2026-09-24", ["can we come back tomorrow", "is the water safe to drink", "what kind of coffee do you grow", "do you have wifi"]),
    ("2026-09-26", ["has the weather changed", "can I pay by card", "how high is the farm", "is that your dog"]),
    ("2026-09-28", ["do you have children", "do you speak English", "can we see the roasting", "is there a bench to sit on"]),
    ("2026-09-30", ["how long have you been farming", "is there wifi", "what else do you grow", "can I take a picture of you"]),
    ("2026-10-02", ["is your coffee certified", "how much for two people", "what birds are those", "where does the coffee end up"]),
]


def main():
    setup = language.load(ROOT)
    code = setup.language.code
    matching = yaml.safe_load((ROOT / "config/matching.yaml").read_text())
    entries = load_guest_bank(ROOT / "config/guest_bank.yaml", code)
    matcher = Matcher(Embedder(setup.matcher), entries)
    translator = Translator(setup.language.translator)
    triggers = Triggers(ROOT / "config/commitment_triggers.yaml")

    real = [json.loads(l) for l in RECORDS.read_text(encoding="utf-8").splitlines() if l.strip()] \
        if RECORDS.exists() else []
    real = [r for r in real if r.get("test_data") is not True]

    test = []
    for v, (day, questions) in enumerate(VISITS, 1):
        start = datetime.fromisoformat(day).replace(hour=14, tzinfo=timezone.utc) + timedelta(minutes=13 * v)
        for q, question in enumerate(questions):
            ranking = matcher.rank(question)
            d = decide(ranking, matching["match_threshold"], triggers.find(question), matching["weak_match_floor"])
            route = NOOR_BANK if (d.route == BANK and question == HANDED_BACK) else d.route
            test.append({
                "id": f"test-{v:02d}-{q + 1}",
                "timestamp": (start + timedelta(minutes=3 * q)).isoformat(timespec="seconds"),
                "visit_id": f"test-visit-{v:02d}",
                "noor_language": code,
                "raw_transcript_en": question,
                "translated_noor": translator.translate(question),
                "matched_entry_id": d.match.entry.id if d.match else None,
                "confidence": round(ranking[0].score, 4) if ranking else None,
                "route": route,
                "intent": d.intent,
                "test_data": True,
                "source": SOURCE,
            })

    RECORDS.parent.mkdir(parents=True, exist_ok=True)
    with open(RECORDS, "w", encoding="utf-8") as f:
        for r in real + test:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    routes = {}
    for r in test:
        routes[r["route"]] = routes.get(r["route"], 0) + 1
    print(f"kept {len(real)} real records; wrote {len(test)} test records in {len(VISITS)} visits: {routes}")


if __name__ == "__main__":
    main()
