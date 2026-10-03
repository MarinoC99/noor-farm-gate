#!/usr/bin/env bash
# One-time fetch and quantization of every model into models/.
#
# This script is the only place in the repo allowed network access (CLAUDE.md rule 1).
# The app never downloads anything; it reads models/ and nothing else.
#
# Every download is pinned to a Hugging Face commit, so a re-run fetches the same bytes.
# Unquantized sources go to .cache/model-src/ and are never shipped or measured.
# Conversion runs in an isolated uv environment (torch, transformers) that the runtime
# never imports.
#
# Usage: scripts/fetch_models.sh        (then: .venv/bin/python scripts/measure_models.py)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODELS="$ROOT/models"
SRC="$ROOT/.cache/model-src"
export HF_HOME="$ROOT/.cache/huggingface"
mkdir -p "$MODELS" "$SRC"

# Pinned revisions, resolved from the Hugging Face API on 2026-10-03.
# whisper-base.en replaced the multilingual whisper-base the same day.
WHISPER_REPO=openai/whisper-base.en   # English-only checkpoint; guests speak English
WHISPER_REV=911407f4214e0e1d82085af863093ec0b66f9cd6
OPUS_REPO=Helsinki-NLP/opus-mt-en-sw
OPUS_REV=28780399d37e1161afc94577a717d7fcfa54fecc
OPUS_ES_REPO=Helsinki-NLP/opus-mt-en-es
OPUS_ES_REV=5bc4493d463cf000c1f0b50f8d56886a392ed4ab
MINILM_REPO=sentence-transformers/all-MiniLM-L6-v2
MINILM_REV=1110a243fdf4706b3f48f1d95db1a4f5529b4d41
PIPER_REPO=rhasspy/piper-voices
PIPER_REV=c10ece1aade47bb51c153c893d14e5bf8e5b7117

# Conversion toolchain. torch 2.2.2 is the last release with Intel macOS wheels, which
# caps transformers at a release that still loads .bin checkpoints with torch<2.6
# (opus-mt-en-sw ships only a .bin). ctranslate2 matches the runtime pin;
# scripts/ct2_convert.py bridges one argument name between it and that transformers.
CONVERT_DEPS=(--with "ctranslate2==4.8.2" --with "transformers==4.46.3" --with "torch==2.2.2"
              --with "numpy<2" --with "sentencepiece==0.2.2" --with "protobuf<5")

fetch() {  # fetch <repo> <rev> <path-in-repo> <dest-file>
  local url="https://huggingface.co/$1/resolve/$2/$3"
  if [[ -s "$4" ]]; then echo "  have $(basename "$4")"; return; fi
  echo "  get  $3"
  mkdir -p "$(dirname "$4")"
  curl -fsSL --retry 3 -o "$4.part" "$url"
  mv "$4.part" "$4"
}

convert() {  # convert <src-dir> <out-dir> <copy-files...>
  local src="$1" out="$2"; shift 2
  if [[ -s "$out/model.bin" ]]; then echo "  have $(basename "$out")/model.bin"; return; fi
  # One thread: torch's OpenMP and the MKL/OpenMP bundled in ctranslate2's Intel macOS
  # wheel segfault together in torch.cat otherwise.
  OMP_NUM_THREADS=1 uv run --no-project --python 3.11 "${CONVERT_DEPS[@]}" \
    python "$ROOT/scripts/ct2_convert.py" --model "$src" --output_dir "$out" \
    --quantization int8 --copy_files "$@" --force
}

echo "== Whisper base.en -> CTranslate2 int8"
W_SRC="$SRC/whisper-base.en"
for f in config.json generation_config.json model.safetensors preprocessor_config.json \
         tokenizer.json tokenizer_config.json vocab.json merges.txt normalizer.json \
         added_tokens.json special_tokens_map.json README.md; do
  fetch "$WHISPER_REPO" "$WHISPER_REV" "$f" "$W_SRC/$f"
done
convert "$W_SRC" "$MODELS/whisper-base.en-ct2-int8" tokenizer.json preprocessor_config.json README.md

echo "== opus-mt-en-sw -> CTranslate2 int8"
O_SRC="$SRC/opus-mt-en-sw"
for f in config.json generation_config.json pytorch_model.bin source.spm target.spm \
         vocab.json tokenizer_config.json README.md; do
  fetch "$OPUS_REPO" "$OPUS_REV" "$f" "$O_SRC/$f"
done
convert "$O_SRC" "$MODELS/opus-mt-en-sw-ct2-int8" source.spm target.spm README.md

echo "== opus-mt-en-es -> CTranslate2 int8"
OES_SRC="$SRC/opus-mt-en-es"
for f in config.json generation_config.json pytorch_model.bin source.spm target.spm \
         vocab.json tokenizer_config.json README.md; do
  fetch "$OPUS_ES_REPO" "$OPUS_ES_REV" "$f" "$OES_SRC/$f"
done
convert "$OES_SRC" "$MODELS/opus-mt-en-es-ct2-int8" source.spm target.spm README.md

echo "== all-MiniLM-L6-v2, 8-bit ONNX (published by the model authors, no conversion)"
# The repo ships one int8 file per CPU family. A phone is arm64; this laptop may not be.
case "$(uname -m)" in
  arm64|aarch64) MINILM_ONNX=onnx/model_qint8_arm64.onnx ;;
  *)             MINILM_ONNX=onnx/model_quint8_avx2.onnx ;;
esac
M_DIR="$MODELS/all-MiniLM-L6-v2-onnx-int8"
fetch "$MINILM_REPO" "$MINILM_REV" "$MINILM_ONNX" "$M_DIR/$(basename "$MINILM_ONNX")"
for f in tokenizer.json config.json README.md; do
  fetch "$MINILM_REPO" "$MINILM_REV" "$f" "$M_DIR/$f"
done

echo "== Piper voices (ONNX as published)"
for v in sw/sw_CD/lanfrica/medium/sw_CD-lanfrica-medium \
         es/es_MX/claude/high/es_MX-claude-high \
         en/en_US/ljspeech/medium/en_US-ljspeech-medium; do
  name="$(basename "$v")"
  for ext in onnx onnx.json; do
    fetch "$PIPER_REPO" "$PIPER_REV" "$v.$ext" "$MODELS/piper/$name/$name.$ext"
  done
  fetch "$PIPER_REPO" "$PIPER_REV" "$(dirname "$v")/MODEL_CARD" "$MODELS/piper/$name/MODEL_CARD"
done
fetch "$PIPER_REPO" "$PIPER_REV" README.md "$MODELS/piper/README.md"

echo "done. Measure with: .venv/bin/python scripts/measure_models.py"
