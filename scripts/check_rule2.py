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

Pending entries (Noor's drafts, records/pending_entries.json; Stage 3), using the real
src/app/drafts.py on a synthetic draft in every state, fully reviewed included, plus
every real queued draft:
  7. a new draft is unverified in both languages, has no English and an unknown
     commitment flag, and is built only from transcripts that got no answer; review
     cannot verify an empty answer, and can remove a guest question but never add one.
     Every line of every draft, verified or not, raises on both paths, with and without
     the flag: the Speaker refuses anything from the drafts file in every mode;
  8. a draft that is not fully verified, routed as a perfect match, never reaches BANK
     without the flag;
  9. no draft is ever loaded into what is matched and spoken: no draft id is in the
     guest bank for any language, only src/web/server.py touches the queue, and the
     server code that does (through any alias, helper or module-level statement) never
     reaches the Speaker, the router or the matcher's entries.
  7 and 9 each hold on their own: the guard does not rely on isolation, nor isolation
  on the guard.

Exits 1 on any failure. Usage: .venv/bin/python scripts/check_rule2.py
"""
import ast
import copy
import logging
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.app import drafts as D  # noqa: E402
from src.pipeline import language  # noqa: E402
from src.pipeline.bank import StopPhrases, load_guest_bank  # noqa: E402
from src.pipeline.route import BANK, Match, Triggers, decide  # noqa: E402
from src.pipeline.speech import Rule2Violation, Speaker  # noqa: E402
from src.web.audio import WebSpeaker  # noqa: E402

CONFIG = ROOT / "config"
PENDING = ROOT / "records" / "pending_entries.json"

# A synthetic gap record and draft for 7-9. Test fixtures, never saved or shown: the
# answer is a marker string, not text in any language.
SYNTHETIC_Q = "synthetic guest question for scripts/check_rule2.py"
SYNTHETIC_A = "synthetic draft answer for scripts/check_rule2.py, never spoken"


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


def pending_drafts(code):
    """(label, draft) for each state, made by the real drafts module, fully reviewed
    included, plus every real queued draft in this language."""
    records = [{"route": "NO_MATCH", "raw_transcript_en": SYNTHETIC_Q, "test_data": True}]
    fresh = D.new_draft(paraphrases=[SYNTHETIC_Q], answer_noor=SYNTHETIC_A, lang=code, records=records)
    out = [("synthetic draft as created", fresh)]
    for en_ok, noor_ok in ((True, False), (False, True), (False, False), (True, True)):
        d = D.review(copy.deepcopy(fresh), answer_en=SYNTHETIC_A, commitment=False, intent="general",
                     verified={"en": en_ok, code: noor_ok})
        out.append((f"synthetic draft reviewed, not a commitment, en verified={en_ok}, "
                    f"{code} verified={noor_ok}", d))
    for d in D.load(PENDING):
        if code in (d.get("verified") or {}):
            out.append((f"queued draft {d['id']}", d))
    return out


def check_creation(code, failures):
    """What "pending" means, asserted on the real module: a new draft is unverified in both
    languages, has no English, is not known to be safe from commitments, and is built only
    from questions guests actually asked that got no answer."""
    records = [{"route": "NO_MATCH", "raw_transcript_en": SYNTHETIC_Q, "test_data": True},
               {"route": "BANK", "raw_transcript_en": "an answered question", "test_data": True}]
    d = D.new_draft(paraphrases=[SYNTHETIC_Q], answer_noor=SYNTHETIC_A, lang=code, records=records)
    if d["verified"] != {code: False, "en": False}:
        failures.append(f"[{code}] a new draft is created with verified {d['verified']}")
    if d["answer_en"] != "":
        failures.append(f"[{code}] a new draft is created with English text")
    if d["commitment"] is not None or d["status"] != "pending":
        failures.append(f"[{code}] a new draft is created with commitment {d['commitment']!r}, "
                        f"status {d['status']!r}")
    for bad in (["a question nobody asked"], ["an answered question"]):
        try:
            D.new_draft(paraphrases=bad, answer_noor=SYNTHETIC_A, lang=code, records=records)
            failures.append(f"[{code}] a draft was built from {bad[0]!r}, not a failed guest question")
        except ValueError:
            pass
        except Exception as e:  # anything but a clean refusal means the check was skipped
            failures.append(f"[{code}] a draft from {bad[0]!r} was not refused cleanly: {e!r}")
    r = D.review(copy.deepcopy(d), answer_en="", commitment=False, intent=None,
                 verified={"en": True, code: True})
    if r["verified"]["en"] or r["status"] != "pending":
        failures.append(f"[{code}] review verified an empty English answer")
    r = D.review(copy.deepcopy(d), answer_en="", commitment=None, intent=None, verified={},
                 paraphrases=[SYNTHETIC_Q, "a question nobody asked"])
    if r["paraphrases_en"] != [SYNTHETIC_Q]:
        failures.append(f"[{code}] review added a guest question: {r['paraphrases_en']}")
    try:
        D.review(copy.deepcopy(d), answer_en="", commitment=None, intent=None, verified={},
                 paraphrases=[])
        failures.append(f"[{code}] review left a draft with no guest question")
    except ValueError:
        pass


def check_pending(code, triggers, threshold, floor, failures):
    check_creation(code, failures)
    drafts = pending_drafts(code)
    strict = {"terminal": Speaker(voices(), play=False).say, "web": WebSpeaker(voices()).say}
    flagged = {"terminal": Speaker(voices(), play=False, allow_unverified=True).say,
               "web": WebSpeaker(voices(), allow_unverified=True).say}
    refused = 0
    speech_log = logging.getLogger("src.pipeline.speech")
    speech_log.disabled = True   # the flag path logs warnings by design; 5 checks those
    try:
        for label, d in drafts:
            e = D.as_entry(d, code)
            lines = (("bank_answer_en", e.answer_en), ("bank_answer_noor", e.answer_noor))
            # 7. The guard: every line, verified or not, every mode, both paths.
            for path, say in {**strict, **{p + "+flag": f for p, f in flagged.items()}}.items():
                for source, line in lines:
                    try:
                        say(source, line)
                        failures.append(f"[{code}/{path}] spoke a draft line {line.origin} ({label})")
                    except Rule2Violation:
                        refused += 1
            # 8. Routing, as a perfect match with its own trigger words.
            if not e.verified:
                for p in e.paraphrases:
                    if decide([Match(e, 1.0, p)], threshold, triggers.find(p), floor).route == BANK:
                        failures.append(f"[{code}] pending {d['id']}: {p!r} routes to BANK ({label})")
    finally:
        speech_log.disabled = False
    # 9, per language: no draft is in the bank this language loads.
    bank_ids = {e.id for e in load_guest_bank(CONFIG / "guest_bank.yaml", code)}
    queued_ids = {d["id"] for d in D.load(PENDING)}
    for i in sorted(bank_ids & queued_ids):
        failures.append(f"[{code}] draft {i} is in guest_bank.yaml")
    for i in sorted(b for b in bank_ids if b.startswith("pending-")):
        failures.append(f"[{code}] guest_bank.yaml has a draft-shaped id {i}")
    print(f"[{code}] drafts checked {len(drafts)} ({len(drafts) - 5} queued): all {refused} draft "
          f"lines refused, verified or not, both paths, with and without the flag; none not fully "
          f"verified reaches BANK")

def _names(node):
    """Every bare name and attribute name used inside a node."""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
    return out


def check_isolation(failures):
    """9. Static: the queue never meets the speaking path. Catches anyone wiring
    src/app/drafts.py or records/pending_entries.json into the matcher, router or
    Speaker in this repo's source; it cannot rule out a path built at runtime."""
    allowed = {"src/app/drafts.py", "src/web/server.py"}
    for py in sorted((ROOT / "src").rglob("*.py")):
        rel = py.relative_to(ROOT).as_posix()
        if rel in allowed:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"))
        text = py.read_text(encoding="utf-8")
        imports = any((isinstance(n, ast.ImportFrom) and n.module and
                       (n.module.endswith("drafts") or any(a.name == "drafts" for a in n.names)))
                      or (isinstance(n, ast.Import) and any(a.name.endswith("drafts") for a in n.names))
                      for n in ast.walk(tree))
        # speech.py names the drafts file only to refuse it (QUEUE_ORIGIN); it may not import it.
        names_file = "pending_entries" in text and rel != "src/pipeline/speech.py"
        if imports or names_file or "as_entry" in text:
            failures.append(f"[isolation] {rel} touches the drafting queue")
    server_src = (ROOT / "src/web/server.py").read_text(encoding="utf-8")
    server = ast.parse(server_src)
    if "as_entry" in server_src:
        failures.append("[isolation] src/web/server.py uses drafts.as_entry, which exists only for this check")

    # Every name a drafts import binds, at any level, under any alias.
    def drafts_imports(node):
        for n in ast.walk(node):
            if isinstance(n, ast.ImportFrom) and n.module:
                if n.module.endswith("drafts"):
                    yield from (a.asname or a.name for a in n.names)
                else:
                    yield from (a.asname or a.name for a in n.names if a.name == "drafts")
            elif isinstance(n, ast.Import):
                yield from (a.asname or a.name.split(".")[0] for a in n.names if a.name.endswith("drafts"))
    aliases = set(drafts_imports(server)) | {"PENDING"}
    functions = [fn for fn in ast.walk(server) if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))]

    def reads_queue_directly(fn):
        return bool(_names(fn) & aliases) or any(True for _ in drafts_imports(fn)) or any(
            isinstance(n, ast.Constant) and isinstance(n.value, str) and "pending_entries" in n.value
            for n in ast.walk(fn))
    touching = {fn.name for fn in functions if reads_queue_directly(fn)}
    while True:   # a function that calls one that reads the queue reads it too
        more = {fn.name for fn in functions if fn.name not in touching and _names(fn) & touching}
        if not more:
            break
        touching |= more
    speaking = {"say", "decide", "Matcher", "rank", "entries", "as_entry", "speaker"}
    for fn in functions:
        if fn.name in touching and speaking & _names(fn):
            failures.append(f"[isolation] src/web/server.py:{fn.lineno} {fn.name} reads the queue "
                            f"and uses {', '.join(sorted(speaking & _names(fn)))}")
    # Module-level statements (outside any def or class) are checked the same way.
    for stmt in server.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
            continue
        names = _names(stmt)
        if (names & (aliases | touching)) and (speaking & names):
            failures.append(f"[isolation] src/web/server.py:{stmt.lineno} module code reads the queue "
                            f"and uses {', '.join(sorted(speaking & names))}")
    touching = len(touching)
    print(f"[isolation] src/: only src/web/server.py reads the queue; its {touching} functions "
          "that do never use the Speaker, the router or the matcher's entries")


def main():
    triggers = Triggers(CONFIG / "commitment_triggers.yaml")
    matching = yaml.safe_load((CONFIG / "matching.yaml").read_text())
    threshold = float(matching["match_threshold"])
    floor = matching.get("weak_match_floor")
    floor = float(floor) if isinstance(floor, (int, float)) else None
    failures = []
    for code in language.available(ROOT):
        check_language(code, triggers, threshold, floor, failures)
        check_pending(code, triggers, threshold, floor, failures)
    check_isolation(failures)
    if failures:
        print("FAIL")
        for f in failures:
            print("  " + f)
        return 1
    print("PASS: without the flag nothing unverified can be spoken, in the terminal or web path, "
          "and only verified entries reach BANK; with it, every unverified line spoken logs a "
          "warning, and nothing unverified reaches the guest in either mode. Drafts are "
          "refused by the guard in every mode and are never loaded to be spoken")
    return 0


if __name__ == "__main__":
    sys.exit(main())
