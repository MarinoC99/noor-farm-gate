"""Audio in and out for the web UI. Wraps the pipeline; changes none of it.

In: the browser's recording (webm/Opus from Chrome and Firefox, mp4/AAC from iOS
Safari) is decoded in memory to 16 kHz float32 for Whisper. Never written to disk.

Out: every sound goes through the pipeline's own Speaker, so its rule-2 guard applies
unchanged, including the limits of --allow-unverified. The Speaker runs muted; the
voices it is handed record what they synthesize, and that audio is returned to the
browser as base64 WAV instead of being played on the laptop.
"""
import base64
import io
import wave

import numpy as np

from src.pipeline.speech import SOURCES, Speaker


def decode_upload(data: bytes, sample_rate: int) -> np.ndarray:
    from faster_whisper import decode_audio
    return decode_audio(io.BytesIO(data), sampling_rate=sample_rate)


def wav_base64(audio: np.ndarray, sample_rate: int) -> str:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(audio.astype(np.int16).tobytes())
    return base64.b64encode(buf.getvalue()).decode("ascii")


class _CapturingVoice:
    """A pipeline Voice that keeps the last audio it synthesized."""

    def __init__(self, voice):
        self.voice = voice
        self.sample_rate = voice.sample_rate
        self.last = None

    def synthesize(self, text):
        self.last = self.voice.synthesize(text)
        return self.last


class WebSpeaker:
    """Speaker.say, but the audio comes back instead of playing on this machine."""

    def __init__(self, voices: dict, allow_unverified: bool = False):
        self.voices = {k: _CapturingVoice(v) for k, v in voices.items()}
        self.speaker = Speaker(self.voices, play=False, allow_unverified=allow_unverified)

    def say(self, source: str, line) -> dict:
        voice = self.voices[SOURCES[source]]
        voice.last = None
        result = self.speaker.say(source, line)  # raises Rule2Violation on unverified text
        audio = voice.last
        return {
            "source": source,
            "voice": result.voice,
            "text": result.text,
            "seconds": round(result.seconds, 2),
            "audio_wav_b64": None if audio is None else wav_base64(audio, voice.sample_rate),
            "refused": None if audio is not None else result.refused,
            "unverified": result.unverified,
        }
