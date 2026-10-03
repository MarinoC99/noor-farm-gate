# eval/

Two case files hold messages with a required outcome. One JSON object per line:

    {"id": "booking-01", "text": "...", "category": "booking"}

`abstain_cases.jsonl` must return outcome `abstain` (the tool is unsure).
Categories: `low_confidence`, `out_of_scope`.

`route_to_human_cases.jsonl` must return outcome `route_to_human`: no draft at all,
because answering would be a commitment only Noor can make. Categories:
`availability`, `booking`, `date_commitment`, `amount_owed`, `safety_assurance`.

Both come from "The abstain and route-to-human contract" in CLAUDE.md.
`scripts/verify.py` needs at least one case per category, and every case must
return its outcome.

`intent_test.jsonl` (Phase 2) uses the same shape with an `intent` field instead
of `category`. verify.py runs it through the pipeline too, to check that every
reply comes from a template.

The pipeline contract (how verify.py and the harness call the pipeline) is in the
docstring at the top of `scripts/verify.py`.

`results/latest.json` is written by `make eval` and is the only source of
numbers for the README, deck and video script.
