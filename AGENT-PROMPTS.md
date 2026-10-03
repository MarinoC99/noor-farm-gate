# Prompts to send the agent

Fill the bracketed placeholders before sending. Drop `CLAUDE.md` in the repo root
first — the agent reads it automatically and everything below assumes it is there.

---

## Prompt 0 — the compliance check, before any feature code

Send this first. It builds the thing that keeps the rest of the weekend honest.

```
Read CLAUDE.md. Before we build any feature, build the compliance check.

Write scripts/verify.py. It exits non-zero with a clear message on any violation.
It checks:

1. NETWORK. Static-scan everything under src/pipeline/ and src/app/ for network
   calls — fetch, axios, requests, urllib, httpx, socket, any http:// or https://
   literal pointing at an inference endpoint. Allow network only in files under
   src/outbox/ (store-and-forward) and scripts/fetch_models.sh. Fail on anything else.

2. MODEL BUDGET. Sum the bytes of every file under models/. Fail if the total
   exceeds the budget in CLAUDE.md.

3. FIXED ANSWER LIST. Assert every reply the pipeline can emit resolves to a
   template id present in config/responses.yaml. Fail if any code path returns
   free-form text on the guest-facing route.

4. ABSTAIN PATH. Assert the abstain response exists, is reachable, and that the
   cases in eval/abstain_cases.jsonl all return it.

5. DATA INVENTORY. Parse data/INVENTORY.md. Fail if any row is missing source,
   licence, size, or the "does not cover" field. TODO(human) is an acceptable
   value for "does not cover" and only for that field.

6. UNSOURCED NUMBERS. Scan docs/ and README.md for numeric claims. Fail on any
   digit sequence that looks like a result (percentage, ms, MB, score) unless the
   file declares it was generated from eval/results/latest.json.

Add `make verify` to run it. Create stub files and empty configs as needed so the
check runs today and fails loudly on what is missing. Do not write any pipeline
code yet. Show me verify.py before you run it.
```

---

## Prompt 1 — the spine

```
Read CLAUDE.md. Build Phase 1, the thinnest end-to-end path, nothing more.

Target: [browser app with transformers.js + ONNX Runtime Web | React Native/Expo |
Python CLI for the demo].

Pipeline, all on-device:
- Intent classification over this fixed list: price, availability, directions,
  dietary, booking, other. Start with a sentence-transformer embedding plus
  nearest-neighbour over labelled examples from MASSIVE — no fine-tuning yet.
- Translation [VISITOR_LANGUAGE] → [LOCAL_LANGUAGE] using NLLB-200 distilled,
  quantized int8.
- Template selection from config/responses.yaml, slot-filled, rendered in
  [LOCAL_LANGUAGE].
- An approval screen. Nothing sends without a tap.
- The abstain path from CLAUDE.md, wired and visible.

Write config/responses.yaml with six placeholder templates and mark it
TODO(human) at the top — I will write the real copy.

Make `make verify` pass. Then show me one worked example end to end with the
intermediate values at each stage. Do not start the eval harness yet.
```

---

## Prompt 2 — the evidence

```
Read CLAUDE.md. Build Phase 2, the evaluation harness.

eval/ contains:
- intent_test.jsonl — 50 held-out visitor messages, realistic phrasing, typos and
  mixed script included, labelled with intent.
- abstain_cases.jsonl — 15 messages that MUST abstain: out-of-scope requests,
  money questions, date promises, ambiguous one-word messages.
- A translation set drawn from FLORES-200 for the [VISITOR_LANGUAGE] →
  [LOCAL_LANGUAGE] direction.

make eval runs all of it and writes eval/results/latest.json:
  intent accuracy and per-class confusion
  abstain recall on abstain_cases (this one must be 100%)
  chrF against FLORES-200 references
  p50 and p95 latency on CPU, single thread, cold and warm
  total model bytes on disk

Report what you measured. Do not characterise the numbers as good or bad, do not
round them in my favour, and do not write them anywhere outside the results file
yet. If a metric comes out poorly, say so plainly.
```

---

## Prompt 3 — submission materials

```
Read CLAUDE.md. Build Phase 3.

1. docs/DECK.md — slide outline against the Section 08 deliverables: problem
   statement in the required one-sentence form, AI capabilities and why SMS or a
   spreadsheet would not do the same job, tool demo walkthrough, where it sits in
   her day, guardrails. Leave "your take" as TODO(human).

2. docs/VIDEO-SCRIPT.md — timed to 4 minutes, with the offline demonstration as a
   beat: network disabled on camera, feature still working.

3. Populate every number in both documents by reading eval/results/latest.json.
   Cite the file. If a number is not in there, write TODO(measure) — do not supply
   it from memory or from your general knowledge of typical model performance.

4. data/INVENTORY.md — complete every row except the "does not cover" fields,
   which stay TODO(human).

make verify must pass when you are done.
```

---

## Mid-build prompts worth keeping handy

**When it proposes something that smells like a rule violation:**
```
Which rule in CLAUDE.md does that touch, and does it break it? Answer that before
you write any code.
```

**When it reports a phase complete:**
```
Paste the output of `make verify`. Then list every number you wrote into a document
this session and the line in eval/results/latest.json each one came from.
```

**When a metric is disappointing and you are tempted to move on:**
```
Do not tune the threshold to improve this number. Tell me what the number means for
Noor in practice and what the honest limitation statement would be.
```
