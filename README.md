# Noor's farm gate

A tool that does the local guide's job at a coffee farm gate. A guest asks a question
in English. Noor hears it in Spanish and sees it written. The tool reads her an answer
she wrote herself; she taps, and it speaks that answer to the guest in English.

**Every sentence that reaches the guest was written and verified by a human in
advance.** The one unchecked thing the tool says is the guest's own question,
machine-translated and spoken only to Noor, in front of the guest who asked it, so she
knows what was asked. Questions about dates, money or safety always stop and hand back
to Noor, with the reason said out loud in her language. The models run on the laptop
with no network at inference.

Noor's language is one setting, `config/language.yaml`: Spanish by default. Swahili is
kept, selectable, as the documented hard case. Its text is machine-translated and nobody
who speaks Swahili has checked it, so it is marked unverified and speaks only with
`--allow-unverified`. With that flag the tool speaks unverified text to Noor, never to
the guest, logs a warning for every such line, and says on screen that the language is
unverified.

Built for the Small AI for Development hackathon, tourism challenge.

**Status:** Stage 1 only: the guest side, end to end. Noor's own phrase bank (Stage 2)
and the summary view (Stage 3) are not built. Two front ends over the same pipeline: a
terminal app, and a one-page web UI for a phone held between two people. Tested on one
Intel Mac, macOS 15. **Spanish is partly filled:** the stop phrases and sixteen answers
are reviewed by native speakers and verified, and fifteen of those can be spoken (the
sixteenth is a commitment). Every other question stops, saying why in Spanish.

## How it works

| Step | Model | Does |
|---|---|---|
| Hear | Whisper base.en, int8 | Guest's speech → English text. Audio stays in memory and is dropped. |
| Translate | opus-mt-en-es, int8 (Swahili: opus-mt-en-sw) | English → Noor's language, shown and read to her. The only machine-made text the tool ever voices, and only to her. |
| Match | all-MiniLM-L6-v2, 8-bit | Finds the closest question in `config/guest_bank.yaml`. |
| Decide | none (rules) | **BANK** if the match is strong, verified and not a commitment. Otherwise it stops: **COMMITMENT**, **WEAK_MATCH** or **NO_MATCH**. |
| Speak | Piper voices | Noor's language to Noor, English to the guest. |

**Size**, from `results/model_budget.json`, against a 400 MB budget per shipped
language: the Spanish stack a phone would carry is **331.6 MB**; the Swahili stack is
328.3 MB. Everything on the development laptop, both languages, is 454.8 MB; that is not
what ships.

## Run it

Needs Python 3.11, [uv](https://docs.astral.sh/uv/), and a microphone.

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
scripts/fetch_models.sh                    # one-time download + quantize; the only step that uses the network
.venv/bin/python scripts/check_rule2.py    # proves what can and cannot be spoken, both languages
.venv/bin/python -m src.app.stage1         # press Enter, ask a question, press Enter
```

The app refuses to start if Noor's language has unverified stop phrases. Spanish does
not; Swahili does, so the comparison needs the flag:

```bash
.venv/bin/python -m src.app.stage1 --allow-unverified --language sw   # the Swahili comparison
```

No microphone? On a Mac, make test audio with `say`:

```bash
say -o /tmp/q.wav --data-format=LEI16@16000 "where can I park"
.venv/bin/python -m src.app.stage1 --wav /tmp/q.wav
```

The run prints every intermediate value: transcript, translation, top three match
scores, commitment trigger words, which branch fired, and what was spoken. When an
answer is offered, press Enter to play Noor's tap.

### On a phone (web UI)

```bash
.venv/bin/python -m src.web.server         # http://localhost:8000, bound to 0.0.0.0
```

`--language` and `--allow-unverified` work as in the terminal app. The page shows
Noor's language on her side, and a red banner there for as long as unverified text can
be spoken.

On the laptop, open http://localhost:8000. Browsers allow the microphone on localhost.
A phone needs HTTPS for the microphone, so we expose the laptop through a tunnel, for
example `cloudflared tunnel --url http://localhost:8000`, and open the https address on
the phone. Tap **Start** once (it unlocks audio on iOS), then hold the guest's button
to talk.

**The offline path is the terminal app.** The phone setup is the models on the laptop,
with the phone as screen, microphone and speaker, joined by a network link. The server
makes no network call at inference; Python networking is blocked before the models
load. But the link carries the guest's recorded question and the audio played back
across the internet through the tunnel provider. So the phone setup is not offline,
and we use it with our own voices for testing. With a real guest it would break our
own rule that audio is never sent anywhere.

## Demo questions

Recorded runs, Swahili configuration, synthetic `say` voice. They were recorded before
we corrected the Swahili's status; reproducing them now needs `--allow-unverified
--language sw`. The Spanish versions need the Spanish answers first.

| Ask | Should do | What our recorded run did |
|---|---|---|
| "what kind of coffee is this" | BANK: arabica answer | As expected. `results/demo_runs/coffee_variety.json` |
| "how big is your farm" | BANK: farm size answer | Whisper heard "How big is your thumb?". The tool stopped and said "Sijui hili" ("I don't know this one"). `farm_size.json` |
| "where can I park" | BANK: parking answer | Whisper heard "What can I park?", still matched parking, gave the right answer. See the limitation below. `parking.json` |
| "how much does the tour cost" | COMMITMENT: the money stop phrase | As expected. `price_tour.json` |

## Guarantees, and where they are enforced

- **Only verified text reaches the guest.** English answers carry their own `en`
  verification flag and are refused unless it is true, in every mode, including with
  `--allow-unverified` (`src/pipeline/speech.py`).
- **Only verified text reaches Noor by default.** Her answers and stop phrases carry a
  per-language flag. Unverified ones are spoken only with `--allow-unverified`, each
  with a logged warning and an on-screen banner.
- **`scripts/check_rule2.py` checks all of it** against the real files, for every
  language, in the terminal and web paths, with and without the flag.
- **No Swahili in this repo is verified.** It was machine-translated and not reviewed
  by a Swahili speaker. An earlier version of this README said it had been. That was
  wrong.
- **Commitments always stop:** the entry's `commitment` flag, or any word in
  `config/commitment_triggers.yaml` (`src/pipeline/route.py`).
- **No network at inference:** blocked before any model loads (`src/pipeline/offline.py`).
- **No translation of Noor's speech.** She picks pre-written phrases (Stage 2), even in
  Spanish, where an `es→en` model exists. See `docs/LIMITATIONS.md`.

## Limitations

Read `docs/LIMITATIONS.md`. In short: who checked which language; the Spanish voice's
training data is not established; the Swahili voice's licence is not established and
it speaks the Congolese variety; a misheard question can still reach the right answer
without anyone noticing; the smartphone is assumed to be at the farm; this has not run
on a phone yet.

Also: `data/INVENTORY.md` (every model, licence quoted, measured size),
`DECISIONS.md` (why it is built this way), `SPEC-V2.md` (the spec). Every number we
cite comes from a file in `results/`, except two Swahili observations that
`docs/LIMITATIONS.md` marks as such.
