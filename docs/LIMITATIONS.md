# Limitations

What this tool cannot honestly claim. Facts about the voices come from the files that
`scripts/fetch_models.sh` downloads into `models/piper/`, quoted as written. Facts about
the Swahili voice's training dataset come from our own licence research, recorded in
`DECISIONS.md`; they were not re-checked for this document.

## Who checked which language

Noor's language is Spanish by default (`config/language.yaml`). Swahili stays in the
repo, selectable, as the documented hard case.

- **Spanish** answers and stop phrases are written and reviewed by Spanish speakers on
  the team. At the time of writing they are still `TODO(human)` in the files, so the
  Spanish configuration answers nothing yet. A line is marked verified only after one
  of them has read it.
- **Swahili** answers and stop phrases were machine-translated and were not reviewed by
  a Swahili speaker (see "Our Swahili is machine-translated" below).
- **English** answers are written by the team. Each carries its own `en` flag, and the
  tool never speaks an unverified English line to a guest, in any mode.

We could not tell the difference between the two kinds of text from the text alone.
The system enforces the distinction in code, but code cannot tell you whether a human
actually read something: the `verified` flag is only as true as the person who set it.

What the tool says that nobody checked, in every configuration, is the guest's own
question, machine-translated into Noor's language and spoken only to her. Our claim is
that every string that reaches a guest is verified, not that every string is.

## The Spanish voice's training data is not established

Noor hears Spanish from Piper `es_MX-claude-high` (Mexican Spanish). Its `MODEL_CARD`
says, in full, about its data and training:

> ## Dataset
>
> * URL: https://huggingface.co/spaces/HirCoir/Piper-TTS-Spanish
> * License: apache-2.0
>
> ## Training
>
> See URL above

The URL is a Hugging Face Space, not a dataset. We checked it: its README carries
`license: apache-2.0` and says nothing about training data or method. It hosts this
voice's model file next to other voices named `cortana` and `jarvis`. We found no
statement anywhere of what audio the voice was trained on, who recorded it, or
whether it was fine-tuned from another voice. So we cannot say the voice is free of
the lessac lineage that the Swahili voice carries; we can only say nobody has stated
it. The licence line covers the Space. Whether it covers the recordings is unknown.

The voice is swappable, as with Swahili: it reads text that was already chosen and
plays no part in deciding what is said.

## The Swahili voice has no established licence

We use Piper `sw_CD-lanfrica-medium` to speak to Noor. Its licence position is not
established. We use it anyway, knowingly, and this section sets out the whole chain.

**1. The voice has no licence line of its own.** Its `MODEL_CARD` (Piper voices
repository, revision `c10ece1a`) says, in full, about its data and training:

> ## Dataset
>
> * URL: https://lanfrica.com/record/kiswahili-tts-dataset
> * License: See URL
>
> ## Training
>
> Finetuned from U.S. English lessac voice (medium quality).

The repository that hosts every Piper voice carries `license: mit` in its README
metadata. That is a repository-wide tag. It does not address the terms of any voice's
training data, and we do not read it as settling them.

**2. The training data's licence contradicts itself.** The URL leads to a Mendeley
dataset. Its licence field says CC BY 4.0. Its description says non-profit and
educational use only. Both cannot be the operative terms.

**3. The recordings come from an audio Bible.** The rights of the original recording
are a further question we have not resolved.

**4. The voice was fine-tuned from an English voice with a non-commercial licence.**
The base is Piper's `en_US-lessac-medium`. Its `MODEL_CARD` gives:

> * URL: https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/
> * License: https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html

That is the Blizzard Challenge 2013 research licence, which does not permit commercial
use. A fine-tune inherits weights trained on that data.

### Why we use it anyway

We rejected NLLB-200 and MMS for being non-commercial, so this needs explaining.

- **NLLB had a clean replacement at no cost.** Opus-MT does the same job under
  Apache-2.0. No Swahili voice with a clear commercial licence exists, so there is
  nothing to switch to.
- **The voice is swappable.** It reads out text that was already chosen. It plays no
  part in deciding what the tool says. Replacing it changes how Noor hears a sentence,
  not which sentence she hears.
- **The replacement path is known.** If this went live, the fix is to train a Piper
  voice on Mozilla Common Voice Swahili, which is CC0.

### It is the wrong variety of Swahili

The voice is Congolese Swahili (`sw_CD`), not the coastal standard taught in Kenya and
Tanzania. Our Swahili answers came with a judgement on whether that would sound off to
a Kenyan or Tanzanian ear. Neither the answers nor this judgement came from a Swahili
speaker (see "Our Swahili is machine-translated" below). An earlier version of this
document attributed it to "the Swahili speaker who translated and checked our answers".
That was wrong. Quoted here as an unverified opinion:

> Probably yes. Congolese Swahili differs from the coastal standard in accent and
> intonation, and in some vocabulary. It is also less strict about noun-class
> agreement and uses more French loanwords. It should still be fully understandable:
> closer to hearing a regional accent than a wrong language. The text below is
> standard Swahili, so the main risk is the voice sounding foreign, not being
> misunderstood. This is based on general knowledge of the dialects, not on hearing
> the voice. The reliable check is to play these ten lines to one Kenyan and one
> Tanzanian listener and ask what felt off.

By its own account it rests on general knowledge of the dialects, not on hearing the
voice, and it is not a Swahili speaker's view. Nobody has played the voice to Kenyan
or Tanzanian listeners. Until someone does, we do not know how it sounds to them.
TODO(measure): play the Swahili answers to Kenyan and Tanzanian listeners and record
what felt off.

## Our Swahili is machine-translated and nobody checked it

Every Swahili sentence in this repo, the answers in `config/guest_bank.yaml` and the
stop phrases in `config/stop_phrases.yaml`, was produced by machine translation and was
not reviewed by a Swahili speaker. Earlier versions of this repo said they had been
checked by one. That was wrong, and we have corrected it.

They are marked `verified: false`. The tool refuses to speak unverified text. Running
with `--allow-unverified` speaks it to Noor anyway, logs a warning for every unverified
line, and shows on screen that the language is unverified, so the Swahili stays
runnable as a documented hard case, not a verified one. The English answers the guest
hears are verified separately and the flag never relaxes them.

### What we saw in the Swahili configuration

Two problems we saw, recorded here because they are what an unverified language costs.
Neither comes from a results file, so treat both counts as observations, not
measurements:

- **Inbound translation distorted three of five questions.** In one live session
  (one team member's voice, five scripted questions; kept only in the local exchange
  log, not in `results/`, because it is real speech), the Swahili that Noor heard was
  off in three runs even where Whisper heard the English right: "tour" became a
  competition (`mashindano`), "where can I park" gained a garden (`bustani`), and
  "what's the altitude here" became "what is there in the mountains". That reading is
  ours, not a Swahili speaker's.
- **"farm" was mis-transcribed across two speakers.** "How big is your farm" was heard
  as "thumb" from the synthetic `say` voice (`results/demo_runs/farm_size.json`) and as
  "phone", twice, from a team member's voice in the live session. Both times the tool
  stopped instead of answering.

Spanish has not been through the same session yet. TODO(measure).

## The English voice

The guest hears Piper `en_US-ljspeech-medium`. We picked it because it is the one
English Piper voice we checked that avoids the lessac lineage above. Its `MODEL_CARD`:

> * URL: https://keithito.com/LJ-Speech-Dataset/
> * License: public domain

> Trained from scratch [...] on medium quality settings using the LJ Speech dataset.

(The elided words are an epoch count. CLAUDE.md keeps numbers we did not measure out
of our documents.)

The other English voices we checked (`amy`, `ryan`, `alan`, `hfc_female`,
`libritts_r`) are all marked "Finetuned from U.S. English lessac voice" or similar in
their cards. The ljspeech voice's own weights, like every Piper voice, carry only the
repository-wide `license: mit` tag.

## The speech engine is GPL

Both voices run through the `piper-tts` package, which declares
`License: GPL-3.0-or-later` and bundles espeak-ng, also GPL. The GPL permits commercial
use. It does require that anyone who distributes the app distributes its source under
the same terms. For a hackathon entry with public code that costs nothing. A closed
commercial build would need a different phonemizer.

## A misheard question can still get the right answer, and nothing flags it

Noor's check on an answer is hearing the guest's question in Swahili before she taps.
That check is only as good as the transcript underneath it.

When Whisper mishears a question but the matcher still lands on the right entry, Noor
hears the translation of a question nobody asked, followed by the correct answer to
the one that was. Nothing in the tool tells her the two don't fit. She has to notice
the mismatch herself.

Our parking run, in the Swahili configuration, shows it (`results/demo_runs/parking.json`). The test audio said
"where can I park". Whisper wrote "What can I park?". Noor heard "Ninaweza kuegesha
nini?", a faithful translation of the wrong question. The matcher still scored the
parking entry at 0.8684, above the 0.75 threshold, and the tool read her the correct
parking answer. The outcome was right. The chain that is meant to verify it was
broken, and only the matcher's tolerance for wording made up for it.

This is a real gap in the verification chain, not a corner case. The guest's side of
the screen does show the English transcript, so the guest may catch it, but nothing
asks them to.

The same weakness also produces the opposite, safe failure. In our altitude run
(`results/demo_runs/altitude.json`) the audio said "what's the altitude". Whisper
wrote "What's the attitude?", which translated to "Mtazamo ni nini?" (roughly "what
is the outlook?"). The best match scored 0.3491, so the tool said "Sijui hili" and
stopped. It refused rather than guessed.

Both runs used synthetic speech from the macOS `say` command, not a person. How often
this happens with real guests in a field is unmeasured. TODO(measure).

## The phone is assumed to be at the farm

There are two constraints here, and only one is settled.

**Operability is a design claim.** The concept note says Noor uses the smartphone,
which is her daughter's, only when her daughter is home to set it up and show her how.
So the tool must be usable by Noor alone. It opens to one screen and needs one action:
no setup, no navigation, no typing. Her daughter installs the tool and updates both
answer files at weekends. The interface has to meet this claim, and the demo should
show it.

**Physical availability is an assumption.** Her daughter boards at school in the
district town and may take the phone with her. The concept note does not say whether
the phone stays at the farm. We assume it is there when guests arrive. On days it is
not, the guide still does the job, as today. We have not resolved this, and the tool
does nothing about it.

## Less-supported languages: what we found for Croatian

Before Spanish we tried Croatian, and it stopped at the voice:

- **Translation exists.** Helsinki-NLP has no direct `en-hr` model, but the Serbo-
  Croatian `opus-mt-tc-base-en-sh` (`license: cc-by-4.0`) and the South Slavic
  `opus-mt-en-zls` (`license: apache-2.0`) both translate into Croatian with a
  `>>hrv<<` target token.
- **No voice exists.** Piper has no Croatian voice and no Bosnian one. Its only
  "Serbian" voice, `sr_RS-serbski_institut-medium`, is not Serbian: "Serbski institut" is
  the Sorbian Institute, its two speakers are labelled `dsb` and `hsb` (Lower and Upper
  Sorbian), its dataset licence is `https://creativecommons.org/licenses/by-nc-sa/4.0/`
  (non-commercial), and it was "Finetuned from U.S. English lessac voice".

A language with millions of speakers, a translation model and a phonemizer still had
no usable voice. For a less-supported language the gap would start earlier.

## Noor taps; she does not speak

Noor chooses from pre-written phrases instead of speaking freely. The reason is not
that the models are missing.

Whisper's multilingual checkpoints list Swahili and have a built-in speech-to-English
translate task, under `license: apache-2.0` on their model cards. An earlier version
of our notes said no Swahili speech recognition with a commercial licence existed.
That was wrong.

We don't use it because what it produces is free-form English that no human checked,
spoken to a guest. That breaks the rule the whole tool rests on: every sentence that
reaches a guest was written and verified by a human in advance. Any route that
transcribes her Swahili and then machine-translates it has the same problem. A second, smaller reason: how well a
Whisper model small enough for our budget handles Noor's Swahili is unmeasured.

The text-only route is weaker still. There is no `opus-mt-sw-en`, and the only
Swahili-to-English text model, `opus-mt-swc-en`, is trained on Congolese Swahili.

Spanish is different, and that sharpens the point. `Helsinki-NLP/opus-mt-es-en` does
exist (`license: apache-2.0`), so free-form speech from Noor would be technically
possible in Spanish. We kept the fixed bank anyway. It is not a workaround for a
missing model: the safety claim is the point. Whatever reaches the guest was written
and verified in advance, in every language we support.

## This runs on a laptop, not yet on a phone

The prototype is Python on an Intel Mac. The model stack was chosen to fit a phone,
but CTranslate2 and Piper have not been built or run on Android or iOS in this project.
TODO(measure): on-device run.

The 400 MB budget applies to one shipped language stack, because a phone carries one
Noor language. The Spanish stack measures within it; the laptop, which holds both
languages, does not. Both numbers are in `data/INVENTORY.md`, read from
`results/model_budget.json`.

The web UI (`src/web/`) puts the screen, microphone and speaker on a phone, but every
model still runs on the laptop. To reach the laptop from a phone with HTTPS (which
phone browsers require for the microphone), we use a tunnel. That carries the guest's
recorded question and the reply audio across the internet through the tunnel
provider. The laptop makes no network call at inference, but the phone setup as a
whole is not offline, and it sends guest audio somewhere, which our own rules forbid.
We use it only with our own voices. An offline phone setup would need the phone and
laptop on a local network with a certificate the phone trusts; we have not built it.
