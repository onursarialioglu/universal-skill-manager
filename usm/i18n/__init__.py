import json
import locale
import os
from pathlib import Path
from typing import Any, Dict

_CURRENT_LANG = "en"
_CATALOGS: Dict[str, Dict[str, str]] = {}

def _locales_dir() -> Path:
    return Path(__file__).parent / "locales"

def load_catalogs():
    global _CATALOGS
    ld = _locales_dir()
    for f in ld.glob("*.json"):
        lang = f.stem
        try:
            with open(f, "r", encoding="utf-8") as fp:
                _CATALOGS[lang] = json.load(fp)
        except Exception:
            _CATALOGS[lang] = {}

def detect_language() -> str:
    return os.environ.get("USM_LANG", "en")

def set_language(lang: str):
    global _CURRENT_LANG
    _CURRENT_LANG = lang

def get_language() -> str:
    return _CURRENT_LANG

def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    if not _CATALOGS:
        load_catalogs()
    
    catalog = _CATALOGS.get(_CURRENT_LANG) or _CATALOGS.get("en", {})
    template = catalog.get(key)
    if template is None:
        # fallback to English
        template = _CATALOGS.get("en", {}).get(key)
    if template is None:
        template = default if default is not None else key

    try:
        return template.format(**kwargs)
    except Exception:
        return template

# Initial setup
set_language(detect_language())
