"""Stage 1, guest side, one question end to end. Terminal stand-in for the screen.

Noor's language comes from config/language.yaml (default Spanish), or --language.

  guest speaks English -> Whisper -> opus-mt en->Noor's language -> spoken to Noor + shown
  -> MiniLM matches the English question against guest_bank.yaml
       BANK        -> read Noor her answer -> she taps -> English answer to guest
       COMMITMENT  -> say why, in her language -> stop at the Noor's-bank placeholder
                      (the entry's flag, or a trigger word anywhere in the question)
       WEAK_MATCH  -> say so, in her language -> stop at the same placeholder
       NO_MATCH    -> same; recorded apart from WEAK_MATCH for the Stage 3 summary

Prints every intermediate value to the terminal. That trace is the debugging view asked
for in Stage 1; it is not logged or saved anywhere. The one thing written to disk is the
exchange record in records/exchanges.jsonl. Audio is never written.

  .venv/bin/python -m src.app.stage1              # microphone
  .venv/bin/python -m src.app.stage1 --wav F      # test file instead of the microphone
  .venv/bin/python -m src.app.stage1 --mute       # synthesize, but do not play
  .venv/bin/python -m src.app.stage1 --language sw --allow-unverified
                                                  # the Swahili comparison (unverified)
  ... --wav F --trace-out results/demo_runs/x.json --note "what F contains"
                                                  # save the intermediate values as JSON;
                                                  # test files only, never a real guest
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import yaml

from src.pipeline import offline

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
RECORDS = ROOT / "records" / "exchanges.jsonl"


def section(title):
    print(f"\n── {title} " + "─" * max(0, 66 - len(title)))


def screen(side, lines):
    width = 70
    print("┌" + "─" * (width - 2) + "┐")
    print(f"│ {side:<{width - 4}} │")
    for line in lines:
        for i in range(0, max(len(line), 1), width - 4):
            print(f"│ {line[i:i + width - 4]:<{width - 4}} │")
    print("└" + "─" * (width - 2) + "┘")


def report_speech(result):
    flag = ", UNVERIFIED" if result.unverified else ""
    if result.spoken:
        print(f"  [spoken{flag}, {result.voice} voice, {result.seconds:.1f}s] {result.text}")
    elif result.refused and result.refused.startswith("muted"):
        print(f"  [synthesized{flag}, not played: {result.refused}; {result.voice} voice, "
              f"{result.seconds:.1f}s] {result.text}")
    else:
        print(f"  [NOT SPOKEN: {result.refused}] source={result.source} text={result.text!r}")


def record_from_microphone(sample_rate):
    import sounddevice as sd
    chunks = []

    def callback(indata, frames, t, status):
        chunks.append(indata[:, 0].copy())

    input("\nGuest: press Enter, ask your question, then press Enter again.")
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", callback=callback):
        input("  recording... (Enter to stop)")
    return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)


# Set in main(). The banner is set when --allow-unverified is on and Noor's language
# has unverified text; every Noor panel then carries it (CLAUDE.md rule 2b).
NOOR_TITLE = "NOOR"
UNVERIFIED_BANNER = None


def noor_screen(lines):
    banner = [UNVERIFIED_BANNER, ""] if UNVERIFIED_BANNER else []
    screen(NOOR_TITLE, banner + lines)


def noor_bank_placeholder():
    noor_screen([
        "[ NOOR'S BANK: placeholder ]",
        "Stage 2 is not built. Her phrase list will open here.",
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--wav", type=Path, help="audio file to use instead of the microphone")
    parser.add_argument("--mute", action="store_true", help="synthesize speech but do not play it")
    parser.add_argument("--language", help="Noor's language code from config/language.yaml "
                                            "(default: its noor_language)")
    parser.add_argument("--allow-unverified", action="store_true",
                        help="speak Noor-language text not marked verified, logging a warning "
                             "for each line; never applies to the guest (off by default; "
                             "CLAUDE.md rule 2b)")
    parser.add_argument("--trace-out", type=Path,
                        help="write the intermediate values to this JSON file (needs --wav)")
    parser.add_argument("--note", default="", help="with --trace-out: what the test audio contains")
    args = parser.parse_args()
    if args.trace_out and not args.wav:
        parser.error("--trace-out is for test files only: it would write a real guest's words to disk")

    offline.enforce()

    from src.pipeline import language
    from src.pipeline.bank import StopPhrases, load_guest_bank
    from src.pipeline.models import SAMPLE_RATE, Embedder, Transcriber, Translator, Voice
    from src.pipeline.records import append_exchange, new_visit_id
    from src.pipeline.route import BANK, NOOR_BANK, Matcher, Triggers, decide
    from src.pipeline.speech import Speaker

    global NOOR_TITLE, UNVERIFIED_BANNER
    setup = language.load(ROOT, args.language)
    lang = setup.language
    NOOR_TITLE = f"NOOR ({lang.name})"

    section("load")
    print(f"  Noor's language: {lang.name_en} ({lang.code})")
    entries = load_guest_bank(CONFIG / "guest_bank.yaml", lang.code)
    stops = StopPhrases(CONFIG / "stop_phrases.yaml", lang.code)
    matching = yaml.safe_load((CONFIG / "matching.yaml").read_text())
    threshold = float(matching["match_threshold"])
    floor = matching.get("weak_match_floor")
    floor = float(floor) if isinstance(floor, (int, float)) else None
    if floor is not None and floor >= threshold:
        raise ValueError("config/matching.yaml: weak_match_floor must be below match_threshold")
    triggers = Triggers(CONFIG / "commitment_triggers.yaml")
    print(f"  guest bank: {len(entries)} entries, "
          f"{sum(bool(e.paraphrases) for e in entries)} with written paraphrases, "
          f"{sum(e.verified for e in entries)} verified in en+{lang.code}, "
          f"{sum(e.answerable for e in entries)} answerable (verified and commitment: false)")
    print(f"  stop phrases: " + ", ".join(
        f"{k}{'' if l.verified and l.text else ' (UNVERIFIED or TODO)'}" for k, l in stops.lines.items()))
    unverified_stops = [k for k, line in stops.lines.items() if not line.verified]
    if unverified_stops and not args.allow_unverified:
        print(f"\n  REFUSING TO START: {lang.name_en} stop phrases not verified: "
              f"{', '.join(unverified_stops)}.")
        print("  The tool would have to speak them. Run with --allow-unverified to hear")
        print("  unverified text anyway; every unverified line spoken logs a warning.")
        return 2
    if args.allow_unverified:
        print("  --allow-unverified: ON. Unverified lines will be spoken, each with a warning.")
        if unverified_stops or not all(e.answer_noor.verified for e in entries if e.has_answers):
            UNVERIFIED_BANNER = (f"!! UNVERIFIED LANGUAGE: the {lang.name_en} here has not been "
                                 f"checked by a {lang.name_en} speaker")
            print("  " + UNVERIFIED_BANNER)
    print(f"  match threshold: {threshold} (placeholder, see config/matching.yaml)")
    print(f"  weak match floor: {floor if floor is not None else 'not set: WEAK_MATCH is never recorded'}")
    print("  commitment triggers: " + ", ".join(f"{h} {len(t)}" for h, t in triggers.groups))

    timings = {}

    def timed(name, fn, *a):
        t0 = time.perf_counter()
        out = fn(*a)
        timings[name] = time.perf_counter() - t0
        return out

    asr = timed("load whisper", Transcriber, setup.asr)
    mt = timed("load opus-mt", Translator, lang.translator)
    embedder = timed("load minilm", Embedder, setup.matcher)
    voices = {
        "noor": timed(f"load piper {lang.code}", Voice, lang.voice),
        "guest": timed("load piper en", Voice, setup.guest_voice),
    }
    matcher = timed("index bank", Matcher, embedder, entries)
    speaker = Speaker(voices, play=not args.mute, allow_unverified=args.allow_unverified)
    print("  " + ", ".join(f"{k} {v:.2f}s" for k, v in timings.items()))
    timings.clear()
    visit_id = new_visit_id()
    trace = {"input": {"wav": args.wav.name if args.wav else None, "note": args.note},
             "noor_language": lang.code, "allow_unverified": args.allow_unverified,
             "spoken": []}

    def say(source, line):
        result = timed(source, speaker.say, source, line)
        report_speech(result)
        trace["spoken"].append({"source": result.source, "voice": result.voice,
                                "text": result.text, "spoken": result.spoken, "unverified": result.unverified,
                                "refused": result.refused})

    # 1. Guest speaks. Audio stays in memory and is dropped straight after transcription.
    if args.wav:
        from faster_whisper import decode_audio
        audio = decode_audio(str(args.wav), sampling_rate=SAMPLE_RATE)
        source = f"file {args.wav.name} (test input)"
    else:
        audio = record_from_microphone(SAMPLE_RATE)
        source = "microphone"
    section("1. guest audio")
    print(f"  source: {source}, {len(audio) / SAMPLE_RATE:.1f}s at {SAMPLE_RATE} Hz, in memory only")

    transcript = timed("whisper", asr.transcribe, audio)
    del audio
    section("2. raw transcript (Whisper)")
    print(f"  {transcript!r}")
    if not transcript:
        print("  nothing transcribed; no exchange recorded. Ask again.")
        return 1

    translated = timed("opus-mt", mt.translate, transcript)
    section(f"3. translation en->{lang.code} (opus-mt, machine-made: shown and read to Noor only)")
    print(f"  {translated!r}")

    section("4. Noor's screen + her voice")
    screen("GUEST (English)", [transcript])
    noor_screen([translated])
    trace.update(transcript=transcript, translation_noor=translated)
    say("guest_question_noor", translated)

    ranking = timed("match", matcher.rank, transcript)
    section("5. match scores (MiniLM cosine, English question vs. paraphrases)")
    if not ranking:
        print("  no entry has a written paraphrase")
    for i, m in enumerate(ranking[:3], 1):
        e = m.entry
        print(f"  #{i} {m.score:.4f}  {e.id:<16} closest paraphrase: {m.paraphrase!r}")
        print(f"      intent={e.intent or 'TODO'}  commitment={e.commitment_flag!r}  "
              f"verified={e.verified}")

    hits = triggers.find(transcript)
    section("6. commitment trigger words (config/commitment_triggers.yaml)")
    print("  " + (", ".join(f"{term!r} ({heading})" for heading, term in hits) if hits else "none"))

    decision = decide(ranking, threshold, hits, floor, allow_unverified=args.allow_unverified)
    trace.update(
        top3=[{"entry_id": m.entry.id, "score": round(m.score, 4), "closest_paraphrase": m.paraphrase,
               "commitment": m.entry.is_commitment, "verified": m.entry.verified}
              for m in ranking[:3]],
        trigger_hits=[{"heading": h, "term": t} for h, t in hits],
        match_threshold=threshold, weak_match_floor=floor,
        route=decision.route, reason=decision.reason)
    section(f"7. branch fired: {decision.route}")
    print(f"  why: {decision.reason}")

    route = decision.route
    if route == BANK:
        entry = decision.match.entry
        noor_screen([entry.answer_noor.text, "", "[ Enter: speak it to the guest ]",
                     "[ n + Enter: don't ]"])
        say("bank_answer_noor", entry.answer_noor)
        tap = input("  Noor: ").strip().lower()
        if tap == "n":
            print("  Noor declined. Nothing said to the guest.")
            route = NOOR_BANK
            noor_bank_placeholder()
        else:
            screen("GUEST (English)", [entry.answer_en.text])
            say("bank_answer_en", entry.answer_en)
    else:
        key, phrase = stops.resolve(decision.stop_phrase_key)
        print(f"  stop phrase: {decision.stop_phrase_key} -> stop_phrases.yaml `{key}`")
        say("stop_phrase", phrase)
        noor_bank_placeholder()

    matched = decision.match
    record = append_exchange(
        RECORDS,
        visit_id=visit_id,
        noor_language=lang.code,
        raw_transcript_en=transcript,
        translated_noor=translated,
        matched_entry_id=matched.entry.id if matched else None,
        confidence=ranking[0].score if ranking else None,
        route=route,
        intent=decision.intent,
    )
    section(f"8. exchange record appended to {RECORDS.relative_to(ROOT)}")
    for k, v in record.items():
        print(f"  {k}: {v!r}")

    section("timings")
    print("  " + ", ".join(f"{k} {v:.2f}s" for k, v in timings.items()))

    if args.trace_out:
        trace["route_recorded"] = route
        args.trace_out.parent.mkdir(parents=True, exist_ok=True)
        args.trace_out.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n")
        print(f"\n  trace written to {args.trace_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
