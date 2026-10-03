# Limitations

Source for the limitations slide. Every figure here is cited or comes from
`eval/results/latest.json` (`scripts/verify.py`, numbers check).

## Translation covers one direction: English into Swahili

The tool translates a visitor's enquiry into Swahili so Noor can read it, using
Helsinki-NLP [`opus-mt-en-sw`](https://huggingface.co/Helsinki-NLP/opus-mt-en-sw)
(Marian, Apache-2.0 per its model card). Replies are not machine-translated: they
are pre-translated template pairs checked by a person.

We dropped NLLB-200. It is licensed CC-BY-NC-4.0, and Meta's
[model card](https://huggingface.co/facebook/nllb-200-distilled-600M) lists
production deployment as out of scope for what it calls a research model. Noor
runs a business.

The cost is coverage. NLLB-200 is one model for 200 languages. Opus-MT is one model
per language pair, and many pairs do not exist. Checked against Helsinki-NLP's
models on Hugging Face on 3 October 2026:

- The concept note draws its tourism constraints from The Gambia. There is no direct
  English→X Opus-MT model for Wolof, Fula or Mandinka. NLLB-200 covers Wolof and
  one Fula variety (Nigerian Fulfulde), not Mandinka.
- There is no direct English→X model for Dyula or Amharic either. NLLB-200 covers
  both.
- Helsinki-NLP also publishes multi-language group models (`opus-mt-en-mul`,
  `opus-mt-en-alv`, `opus-mt-en-nic`, `opus-mt-en-sem`) that may reach some of these
  languages through a target-language token. We have not evaluated them.
- There is no French→Swahili model, so French-speaking visitors are not served. The
  nearest is French→Congo Swahili (`opus-mt-fr-swc`), a different variety.
- Each added language is another model on disk, counted against the model budget.

Moving this tool to a less-supported language means first checking that a pair
exists, then measuring it. It is not a configuration change.

## Why not Google ML Kit on-device translation

We considered it and rejected it.

- **It does run offline.** That was not the problem.
- **It fails the side-loading rule.** Section 06 of the concept note requires model
  files small enough to side-load or send over a weak connection. ML Kit's
  [Android guide](https://developers.google.com/ml-kit/language/translation/android)
  describes language packs downloaded from Google on demand
  (`downloadModelIfNeeded`). It documents no way to bundle a pack with the app,
  copy one from a memory card, or pass one over Bluetooth. Noor buys 3G bundles
  when she can afford them.
- **Google positions it for light use.** Its
  [overview](https://developers.google.com/ml-kit/language/translation) says
  on-device translation is intended for "casual and simple translations" and tells
  developers to evaluate quality for their own use case.
- **It cannot be tuned on local data.** It offers no way to adapt the model.
  Section 02 of the concept note includes training or tuning on local data in what
  Small AI means.
- **It gives us nothing to say on data grounding.** Google does not publish the
  training data, its licence, its size, or what it does not cover. Data grounding is
  15% of the score [cite: Small AI for Development concept note Section 09, 2026, global].

`scripts/verify.py` fails if any code under `src/` downloads model weights at
runtime, so this rule is enforced mechanically rather than by decision.

## Dialect and register

The translation model was trained on OPUS parallel text; its model card does not
list which corpora. The card reports results on one test set (GlobalVoices, news and
blog text), not on visitor messages. We assume the training data skews to standard
written register. How it handles everyday Kenyan or Tanzanian Swahili, Sheng, or
mixed English and Swahili is not measured. Dialect handling is a stated limitation,
not a solved problem.

## Weekend-only use

The tool runs on Noor's daughter's smartphone, which is home at weekends. A guest
who writes on a Monday may wait until the weekend for a reply. At six or seven
visitors a month, one weekly session covers the volume of enquiries. It does not
make replies fast.
