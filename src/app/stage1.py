"""Stage 1, guest side, one question end to end. Terminal stand-in for the screen.

  guest speaks English -> Whisper -> opus-mt en->sw -> Piper speaks it to Noor + shows it
  -> MiniLM matches the English question against guest_bank.yaml
       BANK        -> read Noor the Swahili answer -> she taps -> English answer to guest
       COMMITMENT  -> say why in Swahili -> stop at the Noor's-bank placeholder (Stage 2)
                      (the entry's flag, or a trigger word anywhere in the question)
       WEAK_MATCH  -> say so in Swahili  -> stop at the same placeholder
       NO_MATCH    -> same; recorded apart from WEAK_MATCH for the Stage 3 summary

Prints every intermediate value to the terminal. That trace is the debugging view asked
for in Stage 1; it is not logged or saved anywhere. The one thing written to disk is the
exchange record in records/exchanges.jsonl. Audio is never written.

  .venv/bin/python -m src.app.stage1              # microphone
  .venv/bin/python -m src.app.stage1 --wav F      # test file instead of the microphone
  .venv/bin/python -m src.app.stage1 --mute       # synthesize, but do not play
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
MODELS = ROOT / "models"
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
    if result.spoken:
        print(f"  [spoken, {result.voice} voice, {result.seconds:.1f}s] {result.text}")
    elif result.refused and result.refused.startswith("muted"):
        print(f"  [synthesized, not played: {result.refused}; {result.voice} voice, "
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


def noor_bank_placeholder():
    screen("NOOR (Kiswahili)", [
        "[ NOOR'S BANK: placeholder ]",
        "Stage 2 is not built. Her phrase list will open here.",
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--wav", type=Path, help="audio file to use instead of the microphone")
    parser.add_argument("--mute", action="store_true", help="synthesize speech but do not play it")
    parser.add_argument("--trace-out", type=Path,
                        help="write the intermediate values to this JSON file (needs --wav)")
    parser.add_argument("--note", default="", help="with --trace-out: what the test audio contains")
    args = parser.parse_args()
    if args.trace_out and not args.wav:
        parser.error("--trace-out is for test files only: it would write a real guest's words to disk")

    offline.enforce()

    from src.pipeline.bank import StopPhrases, load_guest_bank
    from src.pipeline.models import SAMPLE_RATE, Embedder, Transcriber, Translator, Voice
    from src.pipeline.records import append_exchange, new_visit_id
    from src.pipeline.route import BANK, NOOR_BANK, Matcher, Triggers, decide
    from src.pipeline.speech import Speaker

    section("load")
    entries = load_guest_bank(CONFIG / "guest_bank.yaml")
    stops = StopPhrases(CONFIG / "stop_phrases.yaml")
    matching = yaml.safe_load((CONFIG / "matching.yaml").read_text())
    threshold = float(matching["match_threshold"])
    floor = matching.get("weak_match_floor")
    floor = float(floor) if isinstance(floor, (int, float)) else None
    if floor is not None and floor >= threshold:
        raise ValueError("config/matching.yaml: weak_match_floor must be below match_threshold")
    triggers = Triggers(CONFIG / "commitment_triggers.yaml")
    print(f"  guest bank: {len(entries)} entries, "
          f"{sum(bool(e.paraphrases) for e in entries)} with written paraphrases, "
          f"{sum(e.verified for e in entries)} verified, "
          f"{sum(e.answerable for e in entries)} answerable (verified and commitment: false)")
    print(f"  stop phrases: " + ", ".join(
        f"{k}{'' if l.verified and l.text else ' (UNVERIFIED or TODO)'}" for k, l in stops.lines.items()))
    print(f"  match threshold: {threshold} (placeholder, see config/matching.yaml)")
    print(f"  weak match floor: {floor if floor is not None else 'not set: WEAK_MATCH is never recorded'}")
    print("  commitment triggers: " + ", ".join(f"{h} {len(t)}" for h, t in triggers.groups))

    timings = {}

    def timed(name, fn, *a):
        t0 = time.perf_counter()
        out = fn(*a)
        timings[name] = time.perf_counter() - t0
        return out

    asr = timed("load whisper", Transcriber, MODELS / "whisper-base.en-ct2-int8")
    mt = timed("load opus-mt", Translator, MODELS / "opus-mt-en-sw-ct2-int8")
    embedder = timed("load minilm", Embedder, MODELS / "all-MiniLM-L6-v2-onnx-int8")
    voices = {
        "sw": timed("load piper sw", Voice,
                    MODELS / "piper/sw_CD-lanfrica-medium/sw_CD-lanfrica-medium.onnx"),
        "en": timed("load piper en", Voice,
                    MODELS / "piper/en_US-ljspeech-medium/en_US-ljspeech-medium.onnx"),
    }
    matcher = timed("index bank", Matcher, embedder, entries)
    speaker = Speaker(voices, play=not args.mute)
    print("  " + ", ".join(f"{k} {v:.2f}s" for k, v in timings.items()))
    timings.clear()
    visit_id = new_visit_id()
    trace = {"input": {"wav": args.wav.name if args.wav else None, "note": args.note},
             "spoken": []}

    def say(source, line):
        result = timed(source, speaker.say, source, line)
        report_speech(result)
        trace["spoken"].append({"source": result.source, "voice": result.voice,
                                "text": result.text, "spoken": result.spoken,
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
    section("3. translation en->sw (opus-mt, machine-made: shown and read to Noor only)")
    print(f"  {translated!r}")

    section("4. Noor's screen + her voice")
    screen("GUEST (English)", [transcript])
    screen("NOOR (Kiswahili)", [translated])
    trace.update(transcript=transcript, translation_sw=translated)
    say("guest_question_sw", translated)

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

    decision = decide(ranking, threshold, hits, floor)
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
        screen("NOOR (Kiswahili)", [entry.answer_sw.text, "", "[ Enter: speak it to the guest ]",
                                    "[ n + Enter: don't ]"])
        say("bank_answer_sw", entry.answer_sw)
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
        raw_transcript_en=transcript,
        translated_sw=translated,
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
