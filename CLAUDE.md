# CLAUDE.md — Small AI for Development, Tourism track

## What this project is

An entry for the World Bank Youth Summit × Hack-Nation "Small AI for Development"
hackathon, Tourism sector (Annex C of the concept note). Prototype and a 2–5 minute
video are due at **09:00 on Sunday 4 October 2026**.

**The user we build for.** Noor, 38, a smallholder coffee farmer in the Ondera
highlands who hosts six or seven visitors a month, found by word of mouth. She
speaks Swahili at home and the national language when she has to. Her
own phone is a basic handset used for calls, messages and mobile money. A
smartphone is in the house only when her daughter is home at weekends. No Wi-Fi;
3G data bundles bought as needed. For most of the day she is on the slope and the
phone is at the house.

**The problem.** Visitor enquiries arrive in languages she cannot read. She has no
digital listing. She knows visitors leave happy but not why, and cannot turn a good
review into a referral or a better tour.

**Deployment assumption.** The tool runs on her daughter's smartphone, which is in
the house at weekends. Noor works through enquiries in one weekend session. Six or
seven visitors a month is roughly one enquiry every five days, so a weekly session
covers the load. Do not design for a phone she has every day. A guest may wait
until the weekend for a reply; that is a stated limitation (`docs/LIMITATIONS.md`),
not something to engineer around.

---

## Language and model decisions

Settled 3 October 2026. Do not change any of these without telling the human first.

- **Local language: Swahili.** `swh_Latn` in FLORES-200, `sw` in Opus-MT.
- **Visitor language: English** (`eng_Latn`). A second visitor language was wanted
  if a model pair exists. French has none: Helsinki-NLP publishes no French→Swahili
  Opus-MT model, only French→Congo Swahili (`fr-swc`), a different variety.
- **Translation model: Helsinki-NLP `opus-mt-en-sw`** (Marian), inbound only.
  Apache-2.0 per its Hugging Face model card, which permits commercial use.
  Bundled in `models/`, quantized, side-loadable.
- **Rejected: NLLB-200.** Licensed CC-BY-NC-4.0, and Meta's model card says it is a
  research model not released for production deployment. Noor runs a business.
- **Rejected: Google ML Kit translation.** Its language packs download from Google
  on demand, with no documented way to side-load them. Full reasoning in
  `docs/LIMITATIONS.md`.

---

## Non-negotiable rules

These come from Section 06 and Section 09 of the concept note. Breaking any one of
them loses the entry. Do not design around them, do not propose a "temporary"
exception, and do not defer one to later. If a task appears to require breaking one,
**stop and raise it** rather than proceeding.

1. **No network at inference.** The core feature must run with the device in
   airplane mode. No cloud API, no hosted model endpoint, no fetching weights from a
   CDN at runtime. Weights are bundled or side-loaded once, then used locally.
   Weights are in `models/` before the app starts; no code under `src/` downloads
   them, at runtime or on first launch. Network is permitted only for
   store-and-forward delivery of a message the human has already approved.

2. **Model budget.** Total on-disk weights must stay under 400 MB so the
   bundle can be side-loaded or sent over a weak link. Quantize aggressively. If a
   model will not fit, say so rather than silently swapping in a larger one.

3. **Fixed answer list.** Every reply the tool offers to send is a pre-translated
   template pair (English and Swahili) from `config/responses.yaml`, checked by a
   person who reads both languages. The tool may select and slot-fill a template.
   It may not free-generate or machine-translate text that goes to a guest.
   Translation runs **inbound only**: the visitor's message into Swahili so Noor
   understands the enquiry. There is no outbound translation path.

4. **Abstain, never guess.** Below the confidence threshold the tool returns
   "not sure — ask a person". This path must exist in code, be reachable, and be
   covered by tests.

5. **Human approves before anything leaves the device.** The tool drafts; Noor sends.
   No auto-reply, no auto-booking, no background action on her behalf.

6. **At least one interaction in Swahili**, by voice or text.

---

## The abstain and route-to-human contract

Every message ends in exactly one of three outcomes. Make these concrete in code,
not in prose.

**Draft.** The tool is confident and an approved template answers the message. It
offers that template, slot-filled, for Noor to approve.

**Abstain.** The tool is unsure. It returns the abstain template and does not pick
the argmax anyway.

- Intent confidence below threshold → abstain.
- Message contains a request type outside the fixed intent list → abstain.

**Route to human.** The tool understands the message, but answering it would mean a
commitment only Noor can make. The line is commitment, not topic.

- The tool may state standing facts from approved templates: her usual price, where
  the farm is, what a tour includes.
- It may never make or imply a commitment about a specific date, an amount owed, or
  a safety assurance.
- `availability` and `booking` always route to human, regardless of confidence.
- `dietary` returns a template that defers confirmation to arrival. It never assures
  that an allergy is safe.
- `price` is a template stating her standing rate. It is not a negotiation.
- Route to human means **no draft at all**: a blank compose box with the translated
  enquiry shown above it. A half-draft invites her to send something she did not
  author. This is distinct from abstain.

Translation into Swahili below the quality floor → show the original alongside,
flagged as unverified, whatever the outcome.

Every abstain and every route-to-human must be visible to Noor as what it is. Silent
fallback to a default answer is the failure mode this rule exists to prevent.

---

## Privacy, consent and bias

Responsible AI is pass/fail. These are rules.

- Guest messages stay on the device. Nothing leaves it except a reply Noor sent.
- Guest messages are purged after 30 days.
- No guest data in logs, crash reports or telemetry. `scripts/verify.py` fails on
  any logging call in `src/` that takes a message body, and on any telemetry or
  crash-report SDK.
- The phone is shared. The app opens to compose, never to message history.
- Training data skews to standard register. Dialect handling is a stated
  limitation, not a solved problem.

---

## Data discipline

The entry is scored on data grounding (15%), evidence it works (15%), and a
pass/fail on responsible AI. The guardrail section of our own submission says we
avoid hallucinations, so invented numbers anywhere in this repo are fatal.

- **Never write a figure** into the README, the deck, or any document that you did
  not read out of a results file generated by a script in this repo. If a number is
  not yet measured, write `TODO(measure)`.
- Every dataset used gets a row in `data/INVENTORY.md` with: name, source URL,
  licence, size, and **what it does not cover**. The last field is scored and is
  written by the human — leave it as `TODO(human)`.
- Synthetic data is labelled as synthetic everywhere it appears, including in the
  deck.
- Cite source, year and country for every problem-framing statistic, inline as
  `[cite: source, year, country]` so `scripts/verify.py` can see it.

---

## Decisions you do not make alone

Stop and ask:

- The local language (Swahili), the visitor language (English), the translation
  model (Opus-MT), and any change to them.
- The contents of `config/responses.yaml` — this is a safety surface.
- Anything that stores, transmits or displays a guest's personal data.
- The "what our data does not cover" text.
- The "what localizing AI development means to me" section.

---

## Out of scope for this build

**Review analysis** is the "what happens next" item. It is not built this weekend.
The intended approach is extractive: cluster reviews with the same embedder used for
intent classification and surface real sentences from each cluster. No generation.
If it is built later, its output is shown only to Noor and the code lives outside
`src/pipeline/` and `src/outbox/`, so none of it can reach a guest.

---

## Repo layout

```
config/responses.yaml     approved English + Swahili reply templates, human-authored
models/                   quantized weights, gitignored, fetched by scripts/fetch_models.sh
src/pipeline/             intent → translate (inbound) → draft | abstain | route to human
src/app/                  the phone-sized shell
src/outbox/               store-and-forward for replies Noor approved; the only network code
eval/                     test sets and the harness
eval/results/             JSON written by the harness; the ONLY source of numbers
data/INVENTORY.md         dataset inventory with licences and gaps
scripts/verify.py         the compliance check; its docstring holds the pipeline contract
docs/                     deck outline, video script, LIMITATIONS.md
```

**Pipeline contract.** How the pipeline is called and what it returns is defined in
the docstring at the top of `scripts/verify.py`. Phase 1 implements it exactly;
verify.py and the eval harness drive the pipeline through it.

---

## Definition of done, by phase

**Phase 1 — spine.** One visitor message in English goes end to end: classified,
translated into Swahili for Noor, answered by a draft from a template, an abstain,
or a route to human, and shown for approval. Implements the pipeline contract.
Ugly is fine. `scripts/verify.py` passes.

**Phase 2 — evidence.** `eval/` runs a held-out set and writes
`eval/results/latest.json` with intent accuracy, chrF against FLORES-200
(`eng_Latn` → `swh_Latn`), p50 and p95 latency on CPU, and total model size on disk.
Latency is measured single-threaded, and `latest.json` records the machine it ran on
(CPU model, OS) and the thread count. Abstain and route-to-human cases are in the
test set and are asserted to return those outcomes.

**Phase 3 — proof and submission.** Offline demo recorded with the network
disabled. Deck and video script generated from `eval/results/latest.json`. Dataset
inventory complete except `TODO(human)` fields.

---

## Commands

```
make verify     # run scripts/verify.py — must pass before any commit
make eval       # regenerate eval/results/latest.json
make demo       # run the app locally
```

Run `make verify` before you tell me a phase is complete. If it fails, fix it or
report it. Do not edit `scripts/verify.py` to make a failure go away — if a check is
wrong, say why and wait.
