# CLAUDE.md

Read `SPEC-V2.md` for what we are building and `DECISIONS.md` for what is already
settled. `CONCEPT-NOTE.pdf` is the source of truth — check it yourself rather than
trusting a summary, including mine.

This file is what you may never do. It applies to every session.

---

## The hard rules

**The concept note's own rules (Section 06)** are four, plus two guardrails:

- it runs on a device the user already has;
- its core feature works offline;
- its model files are small enough to side-load or send over a weak connection;
- at least one interaction is in a named local language, by voice or text.
- Guardrail: a person makes the final call; the tool flags what it is unsure of.
- Guardrail: avoid hallucinations.

Section 09 makes Responsible AI pass/fail.

**The six rules below are ours.** Rules 1, 2 and 4 are how we meet the concept note's
rules and guardrails, made stricter. Rules 3, 5 and 6 are our own choices; the concept note does not
ask for them. Do not credit any of the six to the concept note in the README, deck or
video. Hold all six as hard anyway: do not design around them, do not make a
temporary exception, do not defer one. If a task appears to require breaking one,
**stop and say so**.

1. **No network at inference.** *Ours; stricter than "core feature works offline".*
   The tool runs with the device in airplane mode. No cloud API, no hosted model, no
   fetching weights at runtime. Weights are bundled in `models/` before the app
   starts. Network is allowed only in `scripts/` for the one-time model fetch.

2. **The tool speaks only what is in the files, and only verified languages by
   default.** *Ours; how we meet "avoid hallucinations".*

   a) The tool speaks only strings present in `guest_bank.yaml`, `noor_bank.yaml` and
      `stop_phrases.yaml`. Never generated at runtime, in any mode. This is absolute,
      with one exception, inward only: the guest's own question, machine-translated
      into Noor's language, is shown to Noor and spoken only to her, in the presence
      of the person who said it. Those are the guest's own words. Nothing unverified
      ever goes outward to a guest. Our claim is "every string that reaches a guest is
      verified", not "every string is verified". Never write the second.

   b) It speaks a Noor-language string marked unverified only when
      `--allow-unverified` is explicitly set. Each such line logs a warning naming
      where it came from, never its text, and the UI must show that the active
      language is unverified for as long as that mode is on. The flag never applies
      to anything spoken to the guest: an English answer must be verified in every
      mode. `scripts/check_rule2.py` checks both paths, terminal and web.

   Why: a machine draft that a human reads and corrects is verified. A machine draft
   nobody reads is not. Our Swahili is the second case, and we found out only by
   asking. The code can enforce which bucket a string is in; it cannot tell you
   whether a human actually read it.

3. **No translation from Noor's language into English.** *Ours; not in the concept
   note.* Licensed models can do it: Whisper translates Swahili speech straight to
   English, and `opus-mt-es-en` translates Spanish text. We don't use them, because the
   output is free-form English that no human checked, spoken to a guest, which breaks
   rule 2. Noor's side of the conversation is pre-written English.

4. **Commitments always stop.** *Ours; how we meet "a person makes the final call".*
   Dates, money, what is included, any safety assurance. Never auto-answered from the
   bank regardless of match strength. Two triggers, either one enough: the matched
   entry's `commitment` flag, and a word in `config/commitment_triggers.yaml` found in
   the guest's English transcript.

5. **Model budget 400 MB per language stack, quantized.** *Ours; the concept note asks
   only for files small enough to side-load.* A phone ships one Noor language: the
   shared English models, that language's translator and voice, and the phonemizer
   data. That stack must fit. Report both numbers every time: each shipped stack, and
   the dev total of everything in `models/`. Measure them with
   `scripts/measure_models.py`, don't estimate. If a stack will not fit, say so rather
   than quietly swapping in another model.

6. **Licences must permit commercial use, or be documented.** *Ours; the concept
   note asks entrants to check terms, not for this.* Noor runs a business.
   NLLB-200 and MMS are CC-BY-NC and are out, even though the concept note suggests
   them. The Piper Swahili voice is an accepted exception, documented in
   `docs/LIMITATIONS.md`. Check the licence of anything new before proposing it, and
   quote it rather than summarising.

---

## Audio and privacy

Responsible AI is a pass/fail criterion.

- Audio is transcribed and discarded immediately. Never written to disk, never
  logged, never sent anywhere.
- Records hold the question text, the intent and the timestamp. No names, no
  profiles, no guest identifiers.
- No message content in logs, crash reports or telemetry.
- The phone is shared with her daughter. The app must never open into a past
  conversation: it starts on a neutral screen that shows nothing anyone said. What
  guests asked is visible only when someone chooses to look, on Noor's pages (the
  summary, drafting and review), which need the access key. This is a privacy rule,
  not a navigation one: the landing screen is Start.

---

## Numbers

Our submission claims the tool avoids confident wrong answers. Invented figures
anywhere in this repo would undo that.

- Never write a number into the README, the deck, or any document that you did not
  read out of a results file generated by a script in this repo. If it is not
  measured, write `TODO(measure)`.
- Every model gets a row in `data/INVENTORY.md`: name, source, licence quoted, size,
  and what it does not cover.
- Report metrics plainly. Do not call them good, do not round them in our favour. If
  something performs badly, say so.
- Do not tune a threshold to make an eval number look better. If a number is
  disappointing, tell me what it means for Noor in practice.

---

## Decisions you do not make alone

Stop and ask:

- Swapping, adding or removing a model.
- The contents of either bank. These are the safety surface and the actual product.
  Scaffold with `TODO(human)`. **Never generate answer text, in either language.**
- Anything that stores, transmits or displays guest data beyond what is listed above.
- The "what our data does not cover" text.
- Starting a later stage early, or extending scope.

---

## How to work

- One stage at a time. Stage 1 only until I say otherwise.
- Build one path end to end before any polish. Show intermediate values at each
  stage: raw transcript, translation, match scores, which branch fired.
- When you finish something, say what you did **not** do as well as what you did.
- If you disagree with the spec, say so before building it. A contradiction found now
  is cheap; found in code it is not.
- If you find yourself about to say "I'll just use X for now", stop and ask instead.
