# Noor's farm gate

A tool that does the local guide's job at a coffee farm gate. A guest asks a question
in English. Noor hears it in Swahili and sees it written. The tool reads her an answer
she wrote herself; she taps, and it speaks that answer to the guest in English.

**By default it never says a sentence a human did not write and verify in advance.**
Questions about dates, money or safety always stop and hand back to Noor, with the
reason said out loud in Swahili. Everything runs offline.

The exception is `--allow-unverified`, off by default. With it on, the tool speaks our
Swahili, which is machine-translated and unreviewed, and logs a warning for each line.
That mode breaks our own central rule and exists only to keep the Swahili case runnable
for comparison.

Built for the Small AI for Development hackathon, tourism challenge.

**Status:** Stage 1 only: the guest side, end to end. Noor's own phrase bank (Stage 2)
and the summary view (Stage 3) are not built. The interface is a terminal stand-in for
the phone screen. Tested on one Intel Mac, macOS 15.

## How it works

| Step | Model | Does |
|---|---|---|
| Hear | Whisper base.en, int8 | Guest's speech → English text. Audio stays in memory and is dropped. |
| Translate | opus-mt-en-sw, int8 | English → Swahili, shown and read to Noor. The only machine-made text the tool ever voices, and only to her. |
| Match | all-MiniLM-L6-v2, 8-bit | Finds the closest question in `config/guest_bank.yaml`. |
| Decide | none (rules) | **BANK** if the match is strong, verified and not a commitment. Otherwise it stops: **COMMITMENT**, **WEAK_MATCH** or **NO_MATCH**. |
| Speak | Piper voices | Swahili to Noor, English to the guest. |

Model files total 309.2 MB against a 400 MB budget (`results/model_budget.json`).

## Run it

Needs Python 3.11, [uv](https://docs.astral.sh/uv/), and a microphone.

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
scripts/fetch_models.sh                    # one-time download + quantize; the only step that uses the network
.venv/bin/python scripts/check_rule2.py    # proves no unverified text can be spoken
.venv/bin/python -m src.app.stage1 --allow-unverified   # press Enter, ask, press Enter
```

`--allow-unverified` is needed because the Swahili is unverified (see below). Without
it the app refuses to start rather than speak unchecked text.

No microphone? On a Mac, make test audio with `say`:

```bash
say -o /tmp/q.wav --data-format=LEI16@16000 "where can I park"
.venv/bin/python -m src.app.stage1 --allow-unverified --wav /tmp/q.wav
```

The run prints every intermediate value: transcript, translation, top three match
scores, commitment trigger words, which branch fired, and what was spoken. When an
answer is offered, press Enter to play Noor's tap.

## The four demo questions

These runs were recorded before we corrected the Swahili's status; reproducing them now
needs `--allow-unverified`.

| Ask | Should do | What our recorded run did (synthetic `say` voice) |
|---|---|---|
| "what kind of coffee is this" | BANK: arabica answer | As expected. `results/demo_runs/coffee_variety.json` |
| "how big is your farm" | BANK: farm size answer | Whisper heard "How big is your thumb?". The tool stopped and said "Sijui hili" ("I don't know this one"). `farm_size.json` |
| "where can I park" | BANK: parking answer | Whisper heard "What can I park?", still matched parking, gave the right answer. See the limitation below. `parking.json` |
| "how much does the tour cost" | COMMITMENT: "Hili ni kuhusu pesa. Jibu wewe mwenyewe." ("This one is about money — you answer it.") | As expected. `price_tour.json` |

## Guarantees, and where they are enforced

- **Only verified text is spoken by default.** Sources: `config/guest_bank.yaml` and
  `config/stop_phrases.yaml`, entries marked `verified: true`. The speech code raises
  on anything else (`src/pipeline/speech.py`), and `scripts/check_rule2.py` checks the
  real files.
- **No Swahili in this repo is verified.** The Swahili answers and stop phrases were
  machine-translated and were not reviewed by a Swahili speaker. An earlier version of
  this README said they had been checked by one. That was wrong. They are marked
  `verified: false`, so the tool refuses to speak them unless run with
  `--allow-unverified`, which logs a warning for every unverified line it speaks.
- **Commitments always stop:** the entry's `commitment` flag, or any word in
  `config/commitment_triggers.yaml` (`src/pipeline/route.py`).
- **No network at inference:** blocked before any model loads (`src/pipeline/offline.py`).
- **No Swahili → English translation.** Noor will pick pre-written phrases (Stage 2).

## Limitations

Read `docs/LIMITATIONS.md`. In short: the Swahili voice's licence is not established
and it speaks the Congolese variety; a misheard question can still reach the right
answer without anyone noticing; the smartphone is assumed to be at the farm; this has
not run on a phone yet.

Also: `data/INVENTORY.md` (every model, licence quoted, measured size),
`DECISIONS.md` (why it is built this way), `SPEC-V2.md` (the spec). Every number we
cite comes from a file in `results/`.
