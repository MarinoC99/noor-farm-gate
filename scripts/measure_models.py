"""Measure the models against the 400 MB budget (CLAUDE.md rule 5).

The budget is per language stack: a phone ships one Noor language, so the number that
must fit is that language's stack (the shared English models, its translator and
voice, and the phonemizer data the voices need). We also report the dev total, all of
models/ on this laptop with every language.

Writes results/model_budget.json. Every size quoted anywhere in this repo comes from
that file. Sizes are file byte counts (what gets copied to a phone), not estimates.
MB here means 10^6 bytes, the stricter reading of "400 MB".

Also measures runtime data that ships inside Python packages rather than in models/,
so it is visible rather than silently left out of the budget.

Usage: .venv/bin/python scripts/measure_models.py
"""
import hashlib
import importlib.util
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
OUT = ROOT / "results" / "model_budget.json"
BUDGET_BYTES = 400 * 10**6


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dir_bytes(path):
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def package_dir(name):
    spec = importlib.util.find_spec(name)
    return Path(spec.origin).parent if spec and spec.origin else None


def main():
    components = {}
    for top in sorted(p for p in MODELS.iterdir() if p.is_dir()):
        # models/piper holds one directory per voice; count each voice separately.
        groups = [d for d in sorted(top.iterdir()) if d.is_dir()] if top.name == "piper" else [top]
        for group in groups:
            files = sorted(p for p in group.rglob("*") if p.is_file())
            components[str(group.relative_to(MODELS))] = {
                "bytes": sum(p.stat().st_size for p in files),
                "files": {
                    str(p.relative_to(MODELS)): {"bytes": p.stat().st_size, "sha256": sha256(p)}
                    for p in files
                },
            }
    loose = [p for p in MODELS.rglob("*")
             if p.is_file() and p.name != ".gitkeep"
             and not any(str(p.relative_to(MODELS)).startswith(k + "/") for k in components)]
    loose_bytes = sum(p.stat().st_size for p in loose)

    total = sum(c["bytes"] for c in components.values()) + loose_bytes

    # Data the runtime needs that lives in installed packages, not models/.
    outside = {}
    piper_dir = package_dir("piper")
    if piper_dir:
        outside["piper-tts: espeak-ng-data (phonemizer data, used by both voices)"] = \
            dir_bytes(piper_dir / "espeak-ng-data")
        outside["piper-tts: tashkeel (Arabic diacritizer model, bundled, not used)"] = \
            dir_bytes(piper_dir / "tashkeel")
    fw_dir = package_dir("faster_whisper")
    if fw_dir:
        outside["faster-whisper: assets (Silero VAD model, bundled, not used)"] = \
            dir_bytes(fw_dir / "assets")
    used_outside = sum(v for k, v in outside.items() if "not used" not in k)

    # Per-language shipped stacks, from config/language.yaml.
    import yaml
    cfg = yaml.safe_load((ROOT / "config" / "language.yaml").read_text())
    espeak = outside.get("piper-tts: espeak-ng-data (phonemizer data, used by both voices)", 0)

    def model_dir(path):
        p = ROOT / path
        return p if p.is_dir() else p.parent

    shared = {k: model_dir(v) for k, v in cfg["shared"].items()}
    stacks = {}
    for code, lang in cfg["languages"].items():
        parts = dict(shared, translator=model_dir(lang["translator"]), voice=model_dir(lang["voice"]))
        part_bytes = {k: dir_bytes(v) for k, v in parts.items()}
        part_bytes["espeak-ng-data"] = espeak
        total_stack = sum(part_bytes.values())
        stacks[code] = {
            "parts": {k: str(v.relative_to(ROOT)) for k, v in parts.items()},
            "parts_bytes": part_bytes,
            "shared_bytes": sum(part_bytes[k] for k in shared),
            "bytes": total_stack,
            "mb": round(total_stack / 10**6, 1),
            "within_budget": total_stack <= BUDGET_BYTES,
            "headroom_mb": round((BUDGET_BYTES - total_stack) / 10**6, 1),
        }

    result = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "machine": platform.machine(),
        "budget_bytes": BUDGET_BYTES,
        "budget_applies_to": "each shipped language stack (CLAUDE.md rule 5)",
        "stacks": stacks,
        "dev_total_models_dir_bytes": total,
        "dev_total_models_dir_mb": round(total / 10**6, 1),
        "outside_models_dir_bytes": outside,
        "total_including_used_package_data_bytes": total + used_outside,
        "total_including_used_package_data_mb": round((total + used_outside) / 10**6, 1),
        "components": components,
        "loose_files_bytes": loose_bytes,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")

    for name, c in components.items():
        print(f"{c['bytes'] / 10**6:8.1f} MB  {name}")
    if loose_bytes:
        print(f"{loose_bytes / 10**6:8.1f} MB  (loose files)")
    for k, v in outside.items():
        print(f"{v / 10**6:8.1f} MB  [outside models/] {k}")
    print(f"{total / 10**6:8.1f} MB  dev total, all of models/ (every language; not what ships)")
    for code, st in stacks.items():
        print(f"{st['mb']:8.1f} MB  shipped stack '{code}' incl. espeak-ng data   budget "
              f"{BUDGET_BYTES / 10**6:.0f} MB   {'within' if st['within_budget'] else 'OVER'}")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
