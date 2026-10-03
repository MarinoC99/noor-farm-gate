# Limitations

What this tool cannot honestly claim. Facts about the voices come from the files that
`scripts/fetch_models.sh` downloads into `models/piper/`, quoted as written. Facts about
the training dataset come from our own licence research, recorded in `DECISIONS.md`;
they were not re-checked for this document.

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
Tanzania. We asked the Swahili speaker who translated and checked our answers whether
that would sound off to a Kenyan or Tanzanian ear. Their answer, in full:

> Probably yes. Congolese Swahili differs from the coastal standard in accent and
> intonation, and in some vocabulary. It is also less strict about noun-class
> agreement and uses more French loanwords. It should still be fully understandable:
> closer to hearing a regional accent than a wrong language. The text below is
> standard Swahili, so the main risk is the voice sounding foreign, not being
> misunderstood. This is based on general knowledge of the dialects, not on hearing
> the voice. The reliable check is to play these ten lines to one Kenyan and one
> Tanzanian listener and ask what felt off.

That is their judgement from general knowledge of the dialects. Neither they nor we
have played the voice to Kenyan or Tanzanian listeners. Until someone does, we do not
know how it sounds to them. TODO(measure): play the ten verified answers to Kenyan and
Tanzanian listeners and record what felt off.

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

Our parking run shows it (`results/demo_runs/parking.json`). The test audio said
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

## Noor taps; she does not speak

Noor chooses from pre-written phrases instead of speaking freely. The reason is not
that the models are missing.

Whisper's multilingual checkpoints list Swahili and have a built-in speech-to-English
translate task, under `license: apache-2.0` on their model cards. An earlier version
of our notes said no Swahili speech recognition with a commercial licence existed.
That was wrong.

We don't use it because what it produces is free-form English that no human checked,
spoken to a guest. That breaks the rule the whole tool rests on: it only says
sentences a human wrote in advance. Any route that transcribes her Swahili and then
machine-translates it has the same problem. A second, smaller reason: how well a
Whisper model small enough for our budget handles Noor's Swahili is unmeasured.

The text-only route is weaker still. There is no `opus-mt-sw-en`, and the only
Swahili-to-English text model, `opus-mt-swc-en`, is trained on Congolese Swahili.

## This runs on a laptop, not yet on a phone

The prototype is Python on an Intel Mac. The model stack was chosen to fit a phone
(see `data/INVENTORY.md` for measured sizes), but CTranslate2 and Piper have not been
built or run on Android or iOS in this project. TODO(measure): on-device run.
