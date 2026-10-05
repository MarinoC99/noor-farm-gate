# Model inventory

One row per model the tool runs. Licences are quoted verbatim from the card file that
`scripts/fetch_models.sh` downloads next to each model in `models/`. Sizes are read from
`results/model_budget.json`, written by `scripts/measure_models.py` (measured
2026-10-03T23:38:38Z, Intel Mac). MB = 10^6 bytes.

"Does not cover" is scored and is written by a human (CLAUDE.md). It stays
`TODO(human)` until then.

## Models

Noor's language is set in `config/language.yaml`: Spanish by default, Swahili kept as the
documented hard case. The guest side is English for both.

| Model | Role | Source (pinned revision) | Licence, quoted | Size on disk | Does not cover |
|---|---|---|---|---|---|
| Whisper base.en, CTranslate2 int8 | Guest speech → English text (shared) | [openai/whisper-base.en](https://huggingface.co/openai/whisper-base.en) @ `911407f4`, converted by `fetch_models.sh` | `license: apache-2.0` (model card front matter) | 79.8 MB | TODO(human) |
| all-MiniLM-L6-v2, 8-bit ONNX | Matches the English question to a guest bank entry (shared) | [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) @ `1110a243`, `onnx/model_quint8_avx2.onnx` as published | `license: apache-2.0` (model card front matter) | 23.5 MB | TODO(human) |
| Piper en_US-ljspeech-medium | Speaks English to the guest (shared) | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) @ `c10ece1a`, `en/en_US/ljspeech/medium` | Voice card: `License: public domain` (for the dataset). Repository: `license: mit`. | 63.5 MB | TODO(human) |
| opus-mt-en-es, CTranslate2 int8 | English question → Spanish, shown and read to Noor | [Helsinki-NLP/opus-mt-en-es](https://huggingface.co/Helsinki-NLP/opus-mt-en-es) @ `5bc4493d`, converted by `fetch_models.sh` | `license: apache-2.0` (model card front matter) | 82.5 MB | TODO(human) |
| Piper es_MX-claude-high | Speaks Spanish to Noor | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) @ `c10ece1a`, `es/es_MX/claude/high` | Voice card, under Dataset: `License: apache-2.0`; under Training: `See URL above`. Repository: `license: mit`. **Training data not established: see below and `docs/LIMITATIONS.md`.** | 63.1 MB | TODO(human) |
| opus-mt-en-sw, CTranslate2 int8 | English question → Swahili (hard case) | [Helsinki-NLP/opus-mt-en-sw](https://huggingface.co/Helsinki-NLP/opus-mt-en-sw) @ `28780399`, converted by `fetch_models.sh` | `license: apache-2.0` (model card front matter) | 79.1 MB | TODO(human) |
| Piper sw_CD-lanfrica-medium | Speaks Swahili to Noor (hard case) | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) @ `c10ece1a`, `sw/sw_CD/lanfrica/medium` | Voice card: `License: See URL` (for the dataset). Repository: `license: mit`. **Not established: see `docs/LIMITATIONS.md`.** | 63.2 MB | TODO(human) |

## Budget (CLAUDE.md rule 5: 400 MB per shipped language stack)

A phone ships one Noor language: the three shared models above, that language's
translator and voice, and the espeak-ng phonemizer data.

| Stack | Shared models | Translator | Voice | espeak-ng data | Total | Budget |
|---|---|---|---|---|---|---|
| Spanish (`es`), what ships | 166.9 MB | 82.5 MB | 63.1 MB | 19.1 MB | **331.6 MB** | within 400 MB |
| Swahili (`sw`) | 166.9 MB | 79.1 MB | 63.2 MB | 19.1 MB | **328.3 MB** | within 400 MB |

**Dev total**, everything in `models/` on this laptop with both languages:
**454.8 MB**. That is over 400 MB, and it is not what ships.

## Facts from the model cards that bear on coverage

Recorded so whoever writes "does not cover" has them. Not a substitute for that column.

- **Whisper base.en.** The card says the training audio and transcripts were
  "collected from the internet". The dataset itself is not published, so we cannot
  say what accents or recording conditions it under-represents. This is the
  English-only checkpoint, not built for any other language. What it outputs when a
  guest asks in another language is unmeasured. TODO(measure). It replaced the
  multilingual `whisper-base` on 2026-10-03 because guests speak English only. Which
  of the two is more accurate for our guests is unmeasured. TODO(measure).
- **opus-mt-en-es.** A Tatoeba-Challenge `eng-spa` model. The card's pre-processing line
  is "normalization + SentencePiece (spm32k,spm32k)"; the runtime applies the
  SentencePiece step only. Its reported test sets are news and Tatoeba sentences, not
  spoken questions from tourists. Its Spanish variety is not stated.
- **Piper es_MX-claude-high.** The card's Dataset URL is a Hugging Face Space,
  `HirCoir/Piper-TTS-Spanish`, and its Training section says only "See URL above". We
  checked that Space (revision `dd9664ff`): its README carries `license: apache-2.0`
  and no training details. It hosts this voice's ONNX file alongside other voices
  named `cortana` and `jarvis`. Where the training audio came from, and whether the
  voice was fine-tuned from another (for example the lessac voice), is not stated
  anywhere we found. "No lessac lineage" is therefore not established, only
  unstated.
- **opus-mt-en-sw.** The card names its data only as `dataset: opus`, without listing
  corpora. Its one reported benchmark is GlobalVoices (news and blog text), not
  spoken questions from tourists. The card's pre-processing line is "normalization +
  SentencePiece". The runtime applies the SentencePiece step only.
- **all-MiniLM-L6-v2.** The card lists MS MARCO among its fine-tuning datasets, along
  with Reddit, Stack Exchange, and others. The model is English only, which is why it
  matches the guest's English question, not the translation.
- **The Piper voices.** See `docs/LIMITATIONS.md`. The Swahili voice is the Congolese
  variety (`sw_CD`); the Spanish voice is Mexican (`es_MX`, espeak voice `es-419`).
- **The 8-bit MiniLM file is the x86 AVX2 build** because this laptop is Intel. A
  phone would use the `model_qint8_arm64.onnx` file from the same revision.
  TODO(measure): its size.
- **Not used, noted for the record:** `Helsinki-NLP/opus-mt-es-en` exists, also
  `license: apache-2.0`. See `docs/LIMITATIONS.md` for why we don't use it.

## Not in `models/` but shipped with the runtime

Measured by the same script, listed so nothing is quietly left out of the budget.

| What | Comes from | Licence | Size | Used |
|---|---|---|---|---|
| espeak-ng-data (phonemizer) | `piper-tts` 1.8.0 package | package: `GPL-3.0-or-later` | 19.1 MB | yes, by every voice; counted in each stack above |
| tashkeel (Arabic diacritizer model) | `piper-tts` 1.8.0 package | package: `GPL-3.0-or-later` | 4.8 MB | no |
| Silero VAD model | `faster-whisper` 1.2.1 package | package: `MIT` | 1.2 MB | no (VAD is off) |

## Test inputs

Development tests feed Whisper **synthetic speech** generated on this Mac with the
macOS `say` command, from short test questions. Synthetic, one voice, studio-clean.
The runs cited in `docs/LIMITATIONS.md` are saved in `results/demo_runs/`. They show
the path runs. They say nothing about accuracy on real guests in a field.

## Media in the demo video (not part of the tool)

The 60-second demo video is assembled from screenshots of the app, the app's own audio
from one run, and the two items below. Neither ships with the tool.

| Item | Role in the video | Source | Licence, quoted | File | Status |
|---|---|---|---|---|---|
| "Prayer", TRG Banks (album *The Life and Times of Joshua Harris*, 2021) | Ambient bed under the whole video: about -30 LUFS between lines, ducked 10 dB (about -40 LUFS) under every spoken line, faded in and out. | [Free Music Archive track page](https://freemusicarchive.org/music/TRG_Banks/the-life-and-times-of-joshua-harris/prayer-1/); file from `files.freemusicarchive.org`, downloaded 2026-10-04 | Track page: "Prayer by TRG Banks is licensed under a CC0 1.0 Universal License." Album page: "The songs in this album are licensed under: CC0 1.0 Universal". The file carries no licence tag. | `XWQhbjYr2banetgbwxnpR7KvKnCIyp0USbPDQMsG.mp3` (kept as `TRG_Banks_-_prayer.mp3`), 3,187,982 bytes, 320 kbps, 1:20, SHA-256 `dcee335496a17a7b6923585c62a17626a2bad2fc10d6dbc8ba006fce3fa5fc5a` | Usable. CC0 asks for no attribution; credited on the end card and here anyway. Chosen over three other CC0 tracks by the same artist because it has no percussion, which matched the reference the author gave. Its level swells about 10 dB over the track, so it is leveled to sit steady. High-passed at 45 Hz. An earlier cut used "Above the Earth" (same artist, CC0); it was replaced because of its 117 BPM pulse. |
| Guest voice: Marino Coric, the author | Asks the three guest questions; captioned on screen as the author standing in for a visitor | Recorded by the author on 2026-10-04 (`New Recording 6.m4a`, 7.8 s), cut into three clips | His own recording, used with his agreement; no third-party licence applies | Kept outside the repo, like the video | In use. Whisper heard "How much is the tour?" as "How much is the tool?" on the cut clip; the video shows both and says so. |
| macOS system voice "Daniel" (`say -v Daniel`) | Stood in for the guest in two earlier cuts only; not in the current video | macOS Sequoia, on this laptop | macOS Software License Agreement, section F: "you may: (i) use the system voices included in the Apple Software (“System Voices”) (1) while running the Apple Software and (2) to create your own original content and projects for your personal, non-commercial use; [...] No other creation or use of the System Voices [...] is permitted by this License, including but not limited to the use, reproduction, display, performance, recording, publishing or redistribution of any of the System Voices [...] in a profit, non-profit, public sharing or commercial context." | none kept | **Not permitted for the video**, which is why it was replaced. Development use of `say` (see Test inputs) runs while using the Apple software and no recording of it is published; none is in this repo. |
