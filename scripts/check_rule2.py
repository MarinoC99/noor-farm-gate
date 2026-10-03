"""CLAUDE.md rule 2, made executable.

Loads the real config files and checks, for every language in config/language.yaml,
in both speech paths (terminal: src/pipeline/speech.py; web: src/web/audio.py, which
wraps the same Speaker), without loading any model:

Without --allow-unverified (the default):
  1. every unverified line (answer_en, answer_<lang>, stop phrase) makes the Speaker raise;
  2. every verified line can be spoken;
  3. a file source handed a bare string, not a Line from a bank file, raises;
  4. every paraphrase of every entry, routed as a perfect match (score 1.0, with its
     own commitment trigger words), reaches BANK only if both its English and its
     Noor-language answer are verified.

With --allow-unverified's setting on:
  5. every unverified Noor-language line that is spoken logs exactly one warning,
     naming the line's origin and never its text;
  6. an unverified English answer still raises: nothing unverified goes outward to a
     guest, in any mode.

Exits 1 on any failure. Usage: .venv/bin/python scripts/check_rule2.py
"""
import logging
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline import language  # noqa: E402
from src.pipeline.bank import StopPhrases, load_guest_bank  # noqa: E402
from src.pipeline.route import BANK, Match, Triggers, decide  # noqa: E402
from src.pipeline.speech import Rule2Violation, Speaker  # noqa: E402
from src.web.audio import WebSpeaker  # noqa: E402

CONFIG = ROOT / "config"


class SilentVoice:
    sample_rate = 22050

    def synthesize(self, text):
        return np.zeros(1, dtype=np.int16)


class Collect(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def voices():
    return {"noor": SilentVoice(), "guest": SilentVoice()}


def check_language(code, triggers, threshold, floor, failures):
    entries = load_guest_bank(CONFIG / "guest_bank.yaml", code)
    stops = StopPhrases(CONFIG / "stop_phrases.yaml", code)
    file_lines = [(src, line) for e in entries
                  for src, line in (("bank_answer_en", e.answer_en), ("bank_answer_noor", e.answer_noor))]
    file_lines += [("stop_phrase", line) for line in stops.lines.values()]

    def text_of(result):
        return result["text"] if isinstance(result, dict) else result.text

    # 1-3, default mode, both paths.
    strict = {"terminal": Speaker(voices(), play=False).say, "web": WebSpeaker(voices()).say}
    for path, say in strict.items():
        for source, line in file_lines:
            try:
                result = say(source, line)
            except Rule2Violation as e:
                if line.verified:
                    failures.append(f"[{code}/{path}] refused verified {line.origin}: {e}")
                continue
            if not line.verified:
                failures.append(f"[{code}/{path}] spoke unverified {line.origin}")
            elif text_of(result) is None:
                failures.append(f"[{code}/{path}] verified {line.origin} has no text")
        try:
            say("bank_answer_en", "a bare string that is not from any bank file")
            failures.append(f"[{code}/{path}] spoke a bare string")
        except Rule2Violation:
            pass

    # 4. Routing, default mode.
    bank_routes = 0
    for e in entries:
        for p in e.paraphrases:
            d = decide([Match(e, 1.0, p)], threshold, triggers.find(p), floor)
            if d.route == BANK:
                bank_routes += 1
                if not (e.answer_en.verified and e.answer_noor.verified):
                    failures.append(f"[{code}] {e.id}: {p!r} routes to BANK but is not verified")

    # 5-6, with the flag on, both paths.
    speech_log = logging.getLogger("src.pipeline.speech")
    collect = Collect()
    speech_log.addHandler(collect)
    speech_log.propagate = False
    flagged = {"terminal": Speaker(voices(), play=False, allow_unverified=True).say,
               "web": WebSpeaker(voices(), allow_unverified=True).say}
    warned = outward_refused = 0
    try:
        for path, say in flagged.items():
            for source, line in file_lines:
                if line.verified:
                    continue
                collect.records.clear()
                if source == "bank_answer_en":
                    try:
                        say(source, line)
                        failures.append(f"[{code}/{path}+flag] spoke unverified English {line.origin} "
                                        "to the guest")
                    except Rule2Violation:
                        outward_refused += 1
                    continue
                result = say(source, line)
                if text_of(result) is None:
                    continue  # TODO text is refused, not spoken: nothing to warn about
                warnings = [r for r in collect.records if r.levelno == logging.WARNING]
                message = warnings[0].getMessage() if warnings else ""
                if len(warnings) != 1:
                    failures.append(f"[{code}/{path}+flag] {line.origin}: {len(warnings)} warnings, "
                                    "expected 1")
                elif line.origin not in message:
                    failures.append(f"[{code}/{path}+flag] {line.origin}: warning does not name it")
                elif line.text in message:
                    failures.append(f"[{code}/{path}+flag] {line.origin}: warning contains its text")
                else:
                    warned += 1
    finally:
        speech_log.removeHandler(collect)
        speech_log.propagate = True

    verified = sum(e.verified for e in entries)
    print(f"[{code}] entries {len(entries)} ({verified} verified in en+{code}), stop phrases "
          f"{len(stops.lines)} ({sum(l.verified for l in stops.lines.values())} verified), "
          f"paraphrases reaching BANK: {bank_routes}; with the flag: {warned} unverified lines "
          f"spoken with one warning each, {outward_refused} unverified English lines still refused")


def main():
    triggers = Triggers(CONFIG / "commitment_triggers.yaml")
    matching = yaml.safe_load((CONFIG / "matching.yaml").read_text())
    threshold = float(matching["match_threshold"])
    floor = matching.get("weak_match_floor")
    floor = float(floor) if isinstance(floor, (int, float)) else None
    failures = []
    for code in language.available(ROOT):
        check_language(code, triggers, threshold, floor, failures)
    if failures:
        print("FAIL")
        for f in failures:
            print("  " + f)
        return 1
    print("PASS: without the flag nothing unverified can be spoken, in the terminal or web path, "
          "and only verified entries reach BANK; with it, every unverified line spoken logs a "
          "warning, and nothing unverified reaches the guest in either mode")
    return 0


if __name__ == "__main__":
    sys.exit(main())
