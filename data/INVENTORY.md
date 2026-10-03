# Dataset inventory

One row for every dataset or model the tool learns from, is tested against, or
cites for the problem framing (CLAUDE.md, "Data discipline"). `scripts/verify.py`
fails on any row missing source URL, licence, size or "does not cover".

"Does not cover" is scored and written by a human. Leave it as TODO(human).
Synthetic data gets its own row and says "synthetic" in the name. Size is
TODO(measure) until a script in this repo has measured it.

| Name | Source URL | Licence | Size | Does not cover |
|------|------------|---------|------|----------------|
| Helsinki-NLP opus-mt-en-sw (translation model, English→Swahili, trained on OPUS) | https://huggingface.co/Helsinki-NLP/opus-mt-en-sw | Apache-2.0 (Hugging Face model card) | TODO(measure) | TODO(human) |

## Translation model decision, 3 October 2026

- **Using:** Helsinki-NLP `opus-mt-en-sw` (Marian), inbound only: an English visitor
  enquiry translated into Swahili for Noor to read. The Hugging Face model card
  gives the licence as Apache-2.0, which permits commercial use.
- **Replaced:** NLLB-200 distilled. Its licence is CC-BY-NC-4.0 (non-commercial),
  and Meta's model card puts production deployment out of scope for what it calls a
  research model. Noor runs a business, so it is out.
  Source: https://huggingface.co/facebook/nllb-200-distilled-600M
- **Rejected:** Google ML Kit on-device translation. Language packs download from
  Google on demand, with no documented way to side-load them. See
  `docs/LIMITATIONS.md`.
- **What the switch costs:** coverage. Opus-MT has no direct pair for many languages
  NLLB-200 covers, including Wolof, Fula, Dyula and Amharic, and no French→Swahili
  pair. Listed in `docs/LIMITATIONS.md`.
