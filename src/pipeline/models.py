"""The four model wrappers. Each loads from models/ and nothing else."""
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000  # Whisper's input rate


class Transcriber:
    """Whisper base.en (English-only checkpoint), CTranslate2 int8."""

    def __init__(self, model_dir: Path):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(str(model_dir), device="cpu", compute_type="int8",
                                  local_files_only=True)

    def transcribe(self, audio: np.ndarray) -> str:
        """audio: mono float32 at 16 kHz. Never written anywhere."""
        segments, _ = self.model.transcribe(
            audio, language="en", task="transcribe", beam_size=5,
            vad_filter=False, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segments).strip()


class Translator:
    """opus-mt-en-sw, CTranslate2 int8. English to Swahili only; there is no reverse."""

    def __init__(self, model_dir: Path):
        import ctranslate2
        import sentencepiece as spm
        self.translator = ctranslate2.Translator(str(model_dir), device="cpu", compute_type="int8")
        self.source = spm.SentencePieceProcessor(model_file=str(model_dir / "source.spm"))
        self.target = spm.SentencePieceProcessor(model_file=str(model_dir / "target.spm"))

    def translate(self, text: str) -> str:
        tokens = self.source.encode(text, out_type=str) + ["</s>"]
        result = self.translator.translate_batch([tokens], beam_size=4, max_decoding_length=256)
        pieces = [t for t in result[0].hypotheses[0] if t not in ("</s>", "<pad>")]
        return self.target.decode(pieces)


class Embedder:
    """all-MiniLM-L6-v2, 8-bit ONNX. Mean-pooled, L2-normalised sentence vectors."""

    def __init__(self, model_dir: Path):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        onnx_path = next(model_dir.glob("model_*int8*.onnx"))
        self.session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tokenizer.enable_padding()  # pad to the longest in the batch, not to 128

    def embed(self, texts) -> np.ndarray:
        encodings = self.tokenizer.encode_batch(list(texts))
        ids = np.array([e.ids for e in encodings], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self.inputs:
            feeds["token_type_ids"] = np.array([e.type_ids for e in encodings], dtype=np.int64)
        hidden = self.session.run(None, feeds)[0]
        weights = mask[..., None].astype(np.float32)
        pooled = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
        return pooled / np.linalg.norm(pooled, axis=1, keepdims=True)


class Voice:
    """One Piper voice. Returns audio in memory; never writes it."""

    def __init__(self, onnx_path: Path):
        from piper import PiperVoice
        self.voice = PiperVoice.load(str(onnx_path))
        self.sample_rate = self.voice.config.sample_rate

    def synthesize(self, text: str) -> np.ndarray:
        chunks = [c.audio_int16_array for c in self.voice.synthesize(text)]
        return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.int16)
