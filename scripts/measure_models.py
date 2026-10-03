"""Measure what is on disk in models/ against the 400 MB budget (CLAUDE.md rule 5).

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

    result = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "machine": platform.machine(),
        "budget_bytes": BUDGET_BYTES,
        "models_dir_total_bytes": total,
        "models_dir_total_mb": round(total / 10**6, 1),
        "models_dir_within_budget": total <= BUDGET_BYTES,
        "models_dir_headroom_mb": round((BUDGET_BYTES - total) / 10**6, 1),
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
    print(f"{total / 10**6:8.1f} MB  TOTAL models/   budget {BUDGET_BYTES / 10**6:.0f} MB"
          f"   {'within' if total <= BUDGET_BYTES else 'OVER'}")
    for k, v in outside.items():
        print(f"{v / 10**6:8.1f} MB  [outside models/] {k}")
    print(f"{(total + used_outside) / 10**6:8.1f} MB  TOTAL incl. package data the runtime uses")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
