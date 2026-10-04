"""Web UI for Stage 1: one page, the guest's side and Noor's side together.

Noor's language comes from config/language.yaml (default Spanish), or --language.
--allow-unverified works as in the terminal app, and the page shows a banner on Noor's
side for as long as it is on and her language has unverified text (CLAUDE.md rule 2b).

The browser records the guest, POSTs the audio here, and this server runs the same
pipeline modules as the terminal app (src/app/stage1.py), in the same order, with the
same banks, thresholds, triggers and verified guard. It returns every intermediate
value as JSON, plus the audio to play as base64 WAV.

Models run on this machine only. Network is blocked for Python before any model loads
(src/pipeline/offline.py); the listening socket is bound first, because the block
also refuses name lookups for "0.0.0.0".

Flow, one exchange at a time:
  POST /api/ask      guest audio -> transcript, translation, match, branch.
                     BANK: Noor's suggested answer in her language, waiting for her tap.
                     Stops: the stop phrase; the exchange record is written now.
  POST /api/send     Noor taps send: the English answer is spoken; record route BANK.
  POST /api/decline  Noor answers herself: nothing is said; record route NOOR_BANK.
An offered answer that is never sent (a new question arrives, or Start is pressed
again) is recorded as NOOR_BANK: it was handed back to Noor, not said.

  .venv/bin/python -m src.web.server [--host 0.0.0.0] [--port 8000] [--language sw]
                                     [--allow-unverified]
"""
import argparse
import socket
import threading
import time
import uuid
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from src.pipeline import offline

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
RECORDS = ROOT / "records" / "exchanges.jsonl"
PAGE = Path(__file__).resolve().parent / "static" / "index.html"
SUMMARY_PAGE = Path(__file__).resolve().parent / "static" / "summary.html"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# What the stop tells Noor, for the label beside the spoken phrase.
REASON_LABELS = {"money": "money", "date": "date", "safety": "safety",
                 "no_match": "don't know", "default": "commitment"}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
PIPE = None  # set in main(), after the models load


class Pipeline:
    def __init__(self, setup, allow_unverified: bool):
        from src.pipeline.bank import StopPhrases, load_guest_bank
        from src.pipeline.models import SAMPLE_RATE, Embedder, Transcriber, Translator, Voice
        from src.pipeline.records import new_visit_id
        from src.pipeline.route import Matcher, Triggers
        from src.web.audio import WebSpeaker

        self.sample_rate = SAMPLE_RATE
        self.language = setup.language
        self.allow_unverified = allow_unverified
        code = self.language.code
        self.entries = load_guest_bank(CONFIG / "guest_bank.yaml", code)
        self.stops = StopPhrases(CONFIG / "stop_phrases.yaml", code)
        # Is any Noor-language text that could be spoken unverified? Drives the banner.
        self.unverified_stops = [k for k, line in self.stops.lines.items() if not line.verified]
        self.noor_unverified = bool(self.unverified_stops) or not all(
            e.answer_noor.verified for e in self.entries if e.has_answers)
        matching = yaml.safe_load((CONFIG / "matching.yaml").read_text())
        self.threshold = float(matching["match_threshold"])
        floor = matching.get("weak_match_floor")
        self.floor = float(floor) if isinstance(floor, (int, float)) else None
        if self.floor is not None and self.floor >= self.threshold:
            raise ValueError("config/matching.yaml: weak_match_floor must be below match_threshold")
        self.triggers = Triggers(CONFIG / "commitment_triggers.yaml")

        self.asr = Transcriber(setup.asr)
        self.mt = Translator(self.language.translator)
        self.matcher = Matcher(Embedder(setup.matcher), self.entries)
        self.speaker = WebSpeaker({"noor": Voice(self.language.voice),
                                   "guest": Voice(setup.guest_voice)},
                                  allow_unverified=allow_unverified)
        self.new_visit_id = new_visit_id
        self.visit_id = new_visit_id()
        self.pending = None  # a BANK exchange waiting for Noor's tap
        self.lock = threading.Lock()

    # -- records -------------------------------------------------------------------

    def _record(self, ex, route):
        from src.pipeline.records import append_exchange
        return append_exchange(
            RECORDS, visit_id=self.visit_id,
            noor_language=self.language.code,
            raw_transcript_en=ex["transcript"], translated_noor=ex["translation_noor"],
            matched_entry_id=ex["matched_entry_id"], confidence=ex["confidence"],
            route=route, intent=ex["intent"])

    def _close_pending(self):
        """An answer offered but never sent was handed back to Noor."""
        from src.pipeline.route import NOOR_BANK
        if self.pending is not None:
            self._record(self.pending, NOOR_BANK)
            self.pending = None

    # -- endpoints -----------------------------------------------------------------

    def start(self):
        with self.lock:
            self._close_pending()
            self.visit_id = self.new_visit_id()
            return {"language": {"code": self.language.code, "name": self.language.name,
                                 "name_en": self.language.name_en},
                    "allow_unverified": self.allow_unverified,
                    "noor_language_unverified": self.allow_unverified and self.noor_unverified,
                    "verified_entries": sum(e.verified for e in self.entries),
                    "entries": len(self.entries)}

    def ask(self, data: bytes, content_type: str):
        from src.pipeline.route import BANK, decide

        with self.lock:
            self._close_pending()
            t = {}

            def timed(name, fn, *a):
                t0 = time.perf_counter()
                out = fn(*a)
                t[name] = round(time.perf_counter() - t0, 3)
                return out

            audio = timed("decode", self._decode, data)
            seconds_heard = len(audio) / self.sample_rate
            transcript = timed("whisper", self.asr.transcribe, audio)
            del audio, data
            result = {"audio_in": {"content_type": content_type, "seconds": round(seconds_heard, 2)},
                      "transcript": transcript}
            if not transcript:
                result.update(route=None, note="nothing transcribed; no exchange recorded")
                return result

            translated = timed("opus-mt", self.mt.translate, transcript)
            question = timed("speak question", self.speaker.say, "guest_question_noor", translated)
            ranking = timed("match", self.matcher.rank, transcript)
            hits = self.triggers.find(transcript)
            decision = decide(ranking, self.threshold, hits, self.floor,
                              allow_unverified=self.allow_unverified)
            matched = decision.match

            ex = {
                "exchange_id": uuid.uuid4().hex,
                "transcript": transcript,
                "translation_noor": translated,
                "matched_entry_id": matched.entry.id if matched else None,
                "confidence": ranking[0].score if ranking else None,
                "intent": decision.intent,
            }
            result.update(
                exchange_id=ex["exchange_id"],
                noor_language=self.language.code,
                translation_noor=translated,
                speech_question_noor=question,
                top3=[{"entry_id": m.entry.id, "score": round(m.score, 4),
                       "closest_paraphrase": m.paraphrase, "intent": m.entry.intent,
                       "commitment": m.entry.is_commitment, "verified": m.entry.verified}
                      for m in ranking[:3]],
                trigger_hits=[{"heading": h, "term": term} for h, term in hits],
                match_threshold=self.threshold, weak_match_floor=self.floor,
                route=decision.route, reason=decision.reason,
                bank=None, stop=None, record=None,
            )

            if decision.route == BANK:
                entry = matched.entry
                result["bank"] = {
                    "entry_id": entry.id,
                    "answer_noor": entry.answer_noor.text,
                    "answer_noor_verified": entry.answer_noor.verified,
                    "speech_answer_noor": timed("speak answer to noor", self.speaker.say,
                                                "bank_answer_noor", entry.answer_noor),
                }
                ex["entry"] = entry
                self.pending = ex
            else:
                key, line = self.stops.resolve(decision.stop_phrase_key)
                result["stop"] = {
                    "key": key,
                    "reason_label": REASON_LABELS.get(key, key),
                    "text_noor": line.text if line else None,
                    "verified": bool(line and line.verified),
                    "gloss_en": self.stops.gloss_en.get(key),
                    "speech_noor": timed("speak stop phrase", self.speaker.say, "stop_phrase", line),
                }
                result["record"] = self._record(ex, decision.route)
            result["timings_s"] = t
            return result

    def summary(self):
        """Stage 3: counts over the local records file. Read-only; nothing is written."""
        from src.app.summary import load_labels, load_records, summarize
        with self.lock:
            data = summarize(load_records(RECORDS), embedder=self.matcher.embedder,
                             translate=self.mt.translate, triggers=self.triggers,
                             threshold=self.threshold)
        data["language"] = {"code": self.language.code, "name": self.language.name,
                            "name_en": self.language.name_en}
        data.update(load_labels(CONFIG / "ui_labels.yaml", self.language.code))
        return data

    def labels(self):
        from src.app.summary import load_labels
        return load_labels(CONFIG / "ui_labels.yaml", self.language.code)

    def _decode(self, data):
        from src.web.audio import decode_upload
        return decode_upload(data, self.sample_rate)

    def send(self, exchange_id: str):
        from src.pipeline.route import BANK
        with self.lock:
            ex = self._take_pending(exchange_id)
            speech = self.speaker.say("bank_answer_en", ex["entry"].answer_en)
            return {"answer_en": ex["entry"].answer_en.text, "speech_answer_en": speech,
                    "record": self._record(ex, BANK)}

    def decline(self, exchange_id: str):
        from src.pipeline.route import NOOR_BANK
        with self.lock:
            ex = self._take_pending(exchange_id)
            return {"record": self._record(ex, NOOR_BANK)}

    def _take_pending(self, exchange_id):
        if self.pending is None or self.pending["exchange_id"] != exchange_id:
            raise HTTPException(409, "no answer is waiting for this exchange")
        ex, self.pending = self.pending, None
        return ex


@app.get("/")
def page():
    return FileResponse(PAGE, headers={"Cache-Control": "no-store"})


@app.get("/summary")
def summary_page():
    return FileResponse(SUMMARY_PAGE, headers={"Cache-Control": "no-store"})


@app.get("/api/summary")
async def summary():
    return await run_in_threadpool(PIPE.summary)


@app.get("/api/labels")
def labels():
    return PIPE.labels()


@app.post("/api/start")
async def start():
    return await run_in_threadpool(PIPE.start)


@app.post("/api/ask")
async def ask(request: Request):
    data = await request.body()
    if not data:
        raise HTTPException(400, "empty recording")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "recording too large")
    return await run_in_threadpool(PIPE.ask, data, request.headers.get("content-type", ""))


@app.post("/api/send")
async def send(request: Request):
    body = await request.json()
    return await run_in_threadpool(PIPE.send, str(body.get("exchange_id", "")))


@app.post("/api/decline")
async def decline(request: Request):
    body = await request.json()
    return await run_in_threadpool(PIPE.decline, str(body.get("exchange_id", "")))


def main():
    global PIPE
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--language", help="Noor's language code from config/language.yaml")
    parser.add_argument("--allow-unverified", action="store_true",
                        help="speak Noor-language text not marked verified, with a warning per "
                             "line and a banner on the page; never applies to the guest")
    args = parser.parse_args()

    # Bind before blocking the network: the block also refuses the lookup of "0.0.0.0".
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((args.host, args.port))
    offline.enforce()

    from src.pipeline import language
    setup = language.load(ROOT, args.language)
    print(f"Noor's language: {setup.language.name_en} ({setup.language.code}). loading models...",
          flush=True)
    PIPE = Pipeline(setup, args.allow_unverified)
    if PIPE.unverified_stops and not args.allow_unverified:
        raise SystemExit(f"REFUSING TO START: {setup.language.name_en} stop phrases not verified: "
                         f"{', '.join(PIPE.unverified_stops)}. Run with --allow-unverified to "
                         "hear unverified text anyway; every line logs a warning and the page "
                         "shows a banner.")
    if PIPE.noor_unverified and args.allow_unverified:
        print(f"--allow-unverified: ON. Unverified {setup.language.name_en} will be spoken to "
              "Noor, each line with a warning; the page shows a banner.", flush=True)
    print(f"ready: http://localhost:{args.port}  (bound to {args.host}; models local, network blocked)",
          flush=True)
    uvicorn.Server(uvicorn.Config(app, log_level="info")).run(sockets=[sock])


if __name__ == "__main__":
    main()
