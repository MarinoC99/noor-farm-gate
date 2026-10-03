# Decisions

What we've settled and why, in plain English. If you want to change one of these,
say so first — don't just do it.

---

## Who we are building for

Noor, a coffee farmer. Six or seven tourists a month turn up at her farm because
someone told them about it. She doesn't speak their language. Right now a local guide
translates for her.

## What we are building

A phone that does the guide's job. A guest speaks English into it, Noor hears the
question in Swahili, and the phone speaks back an answer she wrote herself.

## The one rule everything else follows from

The tool can only ever say sentences a human wrote in advance. In both directions.

We wrote the answers to the questions guests usually ask. We also wrote the thirty
or so things Noor often needs to say back. The tool picks the right one. It never
makes up a sentence.

Why this matters: if the tool could say anything, nobody could check whether it says
something wrong or harmful. A confident wrong answer about her prices or her food
would cost her money and reputation.

Why it works here: a farm visit is a small world. What grows here, how long is the
tour, what does it cost, can I buy beans, where do I park, can my kids come. Maybe
forty questions covers nearly all of it.

## Noor speaks Swahili. Guests speak English.

Swahili because it's the East African common language and the one where the pieces we
need actually exist. With the time we have, a language with missing pieces is a
project that doesn't finish.

Being honest about what this costs us: Swahili is well-supported by African
standards. Google's offline packs already cover it. We are not solving the hardest
version of this problem.

## Noor doesn't speak into the tool — she taps

We wanted her to speak freely and have the tool translate. We won't, and the reason is
the one rule above, not what models exist.

- **Swahili speech can be turned into English with a licence we could use.**
  Whisper's multilingual checkpoints list Swahili and have a built-in
  speech-to-English translate task, Apache-2.0 on their model cards. An earlier
  version of this file said there was no Swahili speech recognition with a
  commercial licence. That was wrong.
- **What comes out is free-form English that no human checked, spoken to a guest.**
  That breaks the rule everything else follows from. The same is true of any route
  that transcribes her Swahili and machine-translates it.
- **We have not measured how well a model that fits our size limit does on Noor's
  Swahili.** That is a second reason, not the main one.
- The text-only route is weaker still. There is no `opus-mt-sw-en`. The only
  Swahili-to-English text model is trained on Congolese Swahili, which is different
  enough from standard Swahili to matter — different grammar agreement, different
  vocabulary, heavy French borrowing.

So instead she picks from a list of phrases we pre-wrote in both languages. Fewer
options, but every word is verified, and the same safety claim covers her side too.

This turned out to be a better design than the one we wanted.

## The phone: two constraints, not one

We had folded these together. They are different, and only one is settled.

**Operability: settled by the concept note.** The smartphone is her daughter's, and
Noor only really uses it when her daughter is home to set it up and show her how. So
the tool must be usable by Noor alone. It opens to one screen and needs one action:
no setup, no navigation, no typing. Her daughter installs the tool and updates both
answer files at weekends. This is a design claim we make, and the interface has to
meet it.

**Physical availability: assumed, not settled.** Her daughter boards at school in the
district town and may take the phone with her. The concept note doesn't say. We
assume the smartphone is at the farm when guests arrive. On days it is not, the guide
still does the job. This is not resolved.

## Some questions always stop

Anything about a date, money, or safety. The tool says so out loud in Swahili and
hands over to her phrase list.

Why: the tool might have the right words but the wrong facts. The answer file might
say tours run Tuesdays. Only Noor knows she's at the cooperative *this* Tuesday.

## It has to work with no internet

Noor buys small amounts of mobile data when she can afford it, and the phone is often
at the house while she's out on the slope. Everything runs on the phone itself.

## We are not using NLLB or MMS

The obvious translation and speech models, suggested by the concept note itself. Both
are licensed non-commercial only, and Noor runs a business. We use Opus-MT instead,
which permits commercial use.

## The Swahili voice — decided, with a caveat

We checked. The Piper Swahili voice has no licence line of its own. Its training data
is a Mendeley dataset whose licence field says CC BY 4.0 but whose description says
non-profit and educational use only — it contradicts itself. The recordings come from
an audio Bible. And the voice was fine-tuned from an English voice trained on Blizzard
2013 data, whose research licence forbids commercial use.

**We use it anyway, and we document all of that.**

Why this isn't inconsistent with rejecting NLLB: NLLB had a clean replacement
available at no cost. No licensed Swahili voice exists. And the voice is swappable —
it doesn't touch how the tool decides what to say. The replacement path, if this ever
went live, is training a voice on Mozilla Common Voice Swahili, which is CC0.

Also worth naming: the voice is Congolese Swahili, not the coastal standard taught in
Kenya and Tanzania. It will be understood and will sound foreign.

## If we're asked how this does in a less-supported language

We hit the wall inside Swahili itself. The only available voice is the wrong variety.
The only Swahili-to-English text model is trained on a variety our user doesn't speak.
Swahili has around 200 million speakers and is one of the best-resourced African
languages — and we still couldn't get what we needed.

For something like Oromo or Luganda there'd be no translation model at all, and the
tool wouldn't work.

## Size limit: 400 MB

So it can be copied onto a phone without good internet.

## Audio is never saved

Speech becomes text, the recording is thrown away immediately. Nothing stored,
nothing sent.

## We build in three stages

1. **Guest side.** Guest speaks, Noor hears the question, tool reads her the answer,
   she taps, it speaks English. This alone is a working tool.
2. **Noor's phrase list.** Same code, reversed. About ninety minutes.
3. **Summary screen.** How many guests, what they asked, which questions had no
   answer — that last one is the gap between what guests want and what she offers.

Stage 3 is cheap because it's just counting records we're already keeping. Cut it
without regret if time runs out.

## What we are NOT building

- Anything that helps tourists find her
- Anything handling messages sent before a visit
- Anything that updates either answer file by itself
- Anything that sends or says something Noor didn't approve
- Free-form speech from Noor

---

## Deadline

**09:00, Sunday 4 October.**

Stage 1 talking end to end tonight. Stage 2 after. Stop building at a fixed hour and
record the video — an entry without one doesn't reach the shortlist, no matter how
good the code is.

---

## Still to do — not the agent's job

**The two answer files.** Forty guest questions with answers, thirty phrases for
Noor, English and Swahili. This is the real product. The agent builds the container.

**Get a Swahili speaker to check the translations.** If nobody checks them, we say
they're unchecked. We don't imply otherwise.
