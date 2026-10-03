# Noor's farm gate — build spec

> **Language note, 3 October.** Noor's language is now Spanish, set in
> `config/language.yaml`; Swahili remains as the documented hard case. Where this spec
> says Swahili for Noor's side, read "Noor's language". See `DECISIONS.md`.

## What it is

A phone that does the local guide's job at the farm gate.

A guest is standing in front of Noor. They share no language. The guest speaks
English into the phone; Noor hears the question in Swahili and sees it written. The
phone reads her the matching answer — one she wrote herself — she taps, and it speaks
that answer to the guest in English.

When she wants to say something the guest side doesn't cover, she picks from her own
bank of phrases. Those are pre-written in both languages too.

Every exchange becomes a record. A season of conversations becomes three things she
can act on.

## The central property

**Every sentence that reaches a guest was written and verified by a human in
advance.** No generated text goes outward. No thresholds that let unverified text
through. One exception, inward only: the guest's own question, machine-translated, is
spoken to Noor alone, in front of the guest who asked it.

This is possible because the question space at a farm gate is genuinely closed. What
grows here, how long is the tour, what does it cost, can I buy beans, where do I
park, can my children come, can I take photos. Forty entries covers nearly
everything, and the tail is thin.

The architecture fits the problem rather than being imposed on it.

## Why in-person

The concept note says visitors arrive and have help translating through a local
guide, and that the farm is on no digital platform. The guide is the interface: not
always there, costs money, and stands between Noor and her own customers.

Building at the gate needs nothing she doesn't have — no listing, no number in
circulation, no digital presence. Annex C names the absence of a digital listing as
the binding constraint in Jordan, so a tool that assumes one has skipped the hard
part.

## The loop

```
guest taps to speak, in English
  → Whisper (English ASR) → English text
  → Opus-MT en→sw → Swahili text
  → Piper speaks it to Noor in Swahili, AND it appears on screen
  → MiniLM embeds the English question, matches against the GUEST BANK

      ├─ strong match, not a commitment
      │     → Piper reads Noor the Swahili side of that entry
      │     → she taps → Piper speaks the English side to the guest
      │
      ├─ weak match
      │     → "Sijui hili" (I don't know this one), spoken in Swahili
      │     → opens NOOR'S BANK
      │
      └─ commitment (date / money / safety)
            → "Hili ni kuhusu tarehe" (this one is about a date), in Swahili
            → opens NOOR'S BANK

NOOR'S BANK
  → a list of ~30 phrases she commonly needs, in Swahili, large tap targets
  → she taps one → Piper speaks the pre-written English side to the guest
  → she can also tap "I'll handle this myself" and the tool steps out
```

### Why there is no Swahili → English path

`opus-mt-sw-en` does not exist. The only Swahili-source model, `opus-mt-swc-en`, is
trained on Congo Swahili, which differs from the coastal standard in noun-class
agreement, verb marking and vocabulary — a genuine mismatch, not a near-miss.

Speech is different. Whisper's multilingual checkpoints recognise Swahili and
translate it straight to English under Apache-2.0. We don't use them: the output
is free-form English no human checked, spoken to a guest, which breaks the central
property. Their quality on Noor's Swahili at a size that fits is also unmeasured.

So we don't translate her speech. We pre-write it. The constraint produced a better
design: her side is as verifiable as the guest side.

### The three stops

Default is flow. She is standing there watching; a confirmation dialog on every
answer is ceremony, not oversight. The tool stops only where it cannot answer safely:

1. **Weak match** — a question 70% similar to another may be asking something quite
   different. Near-miss retrieval is the dangerous zone.
2. **Commitments** — dates, money, what is included, any safety assurance. The bank
   may say tours run Tuesdays; only Noor knows about *this* Tuesday. Never answered
   from the bank regardless of match strength.
3. **No match at all.**

When the tool stops it says **why**, out loud, in Swahili. A silent handoff looks
broken. A stated limit looks like judgement.

## The two banks

**`config/guest_bank.yaml`** — what guests ask. Each entry:
```yaml
- id: price_tour
  intent: money          # money | general | logistics | safety
  commitment: true       # if true, never auto-answered
  paraphrases_en:
    - "how much is the tour"
    - "what does it cost"
    - "what do you charge"
    - "is it free"
    - "how much for two people"
  answer_en: "..."
  answer_sw: "..."
```

Write paraphrases generously. Absorbing variation in how the same question gets asked
is what makes semantic matching earn its place over keyword search — and it is the
answer to "would a spreadsheet do this job".

**`config/noor_bank.yaml`** — what Noor needs to say. Same shape, no paraphrases:
```yaml
- id: come_back_tuesday
  label_sw: "Rudi Jumanne"
  text_en: "Please come back on Tuesday — I'm at the cooperative today."
```

Both files are human-authored. The agent scaffolds them with `TODO(human)` and never
generates answer text.

## Model stack

| Role | Model | Licence | Notes |
|---|---|---|---|
| Guest ASR | Whisper base.en, int8 | Apache-2.0 / MIT | English only. Training data unpublished — note it. |
| Translation | opus-mt-en-sw, CTranslate2 int8 | Apache-2.0 | No ONNX published; conversion is real work |
| Matching | all-MiniLM-L6-v2, 8-bit ONNX | Apache-2.0 | Runs on the English question. MS MARCO in training data — note it. |
| Swahili TTS | Piper sw_CD-lanfrica-medium | **Not established** | See LIMITATIONS.md. Congo Swahili, not coastal standard. |
| English TTS | Piper English voice | Check MODEL_CARD | Same Blizzard/lessac lineage question |

Budget 400 MB total, quantized. Measure it, don't estimate it.

## Build order

**Stage 1 — the guest side.** Guest speaks, Noor hears and sees the question in
Swahili, bank match, she taps, it speaks English. Records written from the first
exchange. This alone is a working tool.

**Stage 2 — Noor's bank.** The phrase list and the three stops wired to it. Same
matcher, reversed, no new models. Roughly ninety minutes once Stage 1 works.

**Stage 3 — the summary view.** Exchanges counted by intent. Which questions had no
match — that's the gap between what guests want and what she offers.

Stage 3 is a count over records already being written. It is cheap. Do it if time
allows, cut it without regret if not.

**Stretch, only if everything above is recorded:** Noor selects a phrase by speaking
rather than tapping. Needs Swahili ASR. Whisper's multilingual checkpoints are
licensed for it; their accuracy on Noor's Swahili is unmeasured.
Do not start this.

## Data model

```
Exchange: id, timestamp, noor_language, raw_transcript_en, translated_noor,
          matched_entry_id (nullable), confidence, route, intent
route: BANK | NOOR_BANK | WEAK_MATCH | NO_MATCH | COMMITMENT
Visit:    groups exchanges by session
```

Audio is transcribed and discarded. Never written to disk.

## Privacy

- Audio never stored, never leaves the device.
- Records hold the question, the intent and the timestamp. No names, no profiles, no
  guest identifiers.
- No message content in logs or crash reports.
- The phone is shared with her daughter. The app opens to the summary view, never to
  a conversation.

## Interface

One screen, phone-sized, landscape, designed to sit between two people. Guest's side
in English and Noor's side in Swahili, both visible at once. Large tap targets — this
is handed between a stranger and a farmer standing in a field.

Both sides visible is what keeps Noor in the conversation. A design where the guest
holds the phone and the tool answers is just a different black box than the guide.

## Out of scope

Discoverability. Written enquiries before a visit. Any automatic write to either
bank. Any generation. Any Swahili → English translation. Free-form speech from Noor.

## Honest limits

Noor can only say what she anticipated — the same constraint the guest side has, and
defensible for the same reason. The first guest with a genuinely novel question still
waits, and the guide is still needed for that; the tool removes him from the routine,
which is most of it. The Swahili voice is the wrong variety. A conversation mediated
by a phone is slower and stranger than one mediated by a person, and some guests will
not like it.
