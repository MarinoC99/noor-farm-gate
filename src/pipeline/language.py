"""config/language.yaml: which language Noor hears, and the models that go with it."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass(frozen=True)
class Language:
    code: str          # selects answer_<code> and the <code> stop phrases
    name: str          # in the language itself, for Noor's side of the screen
    name_en: str
    translator: Path   # English -> this language
    voice: Path        # Noor's voice


@dataclass(frozen=True)
class Setup:
    language: Language
    asr: Path
    matcher: Path
    guest_voice: Path


def _config(root: Path) -> dict:
    return yaml.safe_load((root / "config" / "language.yaml").read_text(encoding="utf-8"))


def available(root: Path) -> list:
    return list(_config(root)["languages"])


def load(root: Path, code: Optional[str] = None) -> Setup:
    cfg = _config(root)
    code = code or cfg["noor_language"]
    if code not in cfg["languages"]:
        raise ValueError(f"config/language.yaml: no language {code!r}; have {list(cfg['languages'])}")
    lang = cfg["languages"][code]
    shared = cfg["shared"]
    return Setup(
        language=Language(code, lang["name"], lang["name_en"],
                          root / lang["translator"], root / lang["voice"]),
        asr=root / shared["asr"],
        matcher=root / shared["matcher"],
        guest_voice=root / shared["guest_voice"],
    )
