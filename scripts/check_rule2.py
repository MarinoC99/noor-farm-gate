"""CLAUDE.md rule 2, made executable: nothing from an unverified source is ever spoken.

Loads the real config files and checks, without loading any model:
  1. every answer of every `verified: false` entry makes the Speaker raise;
  2. every answer of every `verified: true` entry can be spoken;
  3. the same for every stop phrase;
  4. a bank source handed a bare string, not a Line from a bank file, raises;
  5. every paraphrase of every entry, routed as a perfect match (score 1.0, with its
     own commitment trigger words), reaches BANK only if the entry is verified.

Exits 1 on any failure. Usage: .venv/bin/python scripts/check_rule2.py
"""
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline.bank import StopPhrases, load_guest_bank  # noqa: E402
from src.pipeline.route import BANK, Match, Triggers, decide  # noqa: E402
from src.pipeline.speech import Rule2Violation, Speaker  # noqa: E402

CONFIG = ROOT / "config"


class SilentVoice:
    sample_rate = 22050

    def synthesize(self, text):
        return np.zeros(1, dtype=np.int16)


def main():
    entries = load_guest_bank(CONFIG / "guest_bank.yaml")
    stops = StopPhrases(CONFIG / "stop_phrases.yaml")
    triggers = Triggers(CONFIG / "commitment_triggers.yaml")
    matching = yaml.safe_load((CONFIG / "matching.yaml").read_text())
    threshold = float(matching["match_threshold"])
    floor = matching.get("weak_match_floor")
    floor = float(floor) if isinstance(floor, (int, float)) else None
    speaker = Speaker({"sw": SilentVoice(), "en": SilentVoice()}, play=False)
    failures = []

    def expect_refusal(source, line):
        try:
            speaker.say(source, line)
        except Rule2Violation:
            return
        failures.append(f"spoke unverified {line.origin if hasattr(line, 'origin') else line!r}")

    def expect_speech(source, line):
        try:
            result = speaker.say(source, line)
        except Rule2Violation as e:
            failures.append(f"refused verified {line.origin}: {e}")
            return
        if result.text is None:
            failures.append(f"verified {line.origin} has no text")

    for e in entries:
        for source, line in (("bank_answer_en", e.answer_en), ("bank_answer_sw", e.answer_sw)):
            (expect_speech if e.verified else expect_refusal)(source, line)
    for key, line in stops.lines.items():
        (expect_speech if line.verified else expect_refusal)("stop_phrase", line)
    expect_refusal("bank_answer_en", "a bare string that is not from any bank file")

    bank_routes = 0
    for e in entries:
        for p in e.paraphrases:
            d = decide([Match(e, 1.0, p)], threshold, triggers.find(p), floor)
            if d.route == BANK:
                bank_routes += 1
                if not (e.verified and e.answer_en.verified and e.answer_sw.verified):
                    failures.append(f"{e.id}: {p!r} routes to BANK but is not verified")

    verified = sum(e.verified for e in entries)
    print(f"entries {len(entries)} ({verified} verified), stop phrases {len(stops.lines)}, "
          f"paraphrases routed to BANK as perfect matches: {bank_routes}")
    if failures:
        print("FAIL")
        for f in failures:
            print("  " + f)
        return 1
    print("PASS: no unverified string can be spoken; only verified entries reach BANK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
