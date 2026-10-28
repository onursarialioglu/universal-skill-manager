import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict

def slugify(text: str) -> str:
    # Normalize unicode to ASCII
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)

def compute_json_hash(obj: Any) -> str:
    serialized = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        while chunk := fp.read(8192):
            h.update(chunk)
    return h.hexdigest()

def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "••••••"
    return value[:3] + "••••••" + value[-2:]
