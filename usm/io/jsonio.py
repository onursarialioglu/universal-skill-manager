import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

class JSONFormatInfo:
    def __init__(self, indent: int = 2, newline: str = "\n", had_trailing_newline: bool = True):
        self.indent = indent
        self.newline = newline
        self.had_trailing_newline = had_trailing_newline

def detect_format(raw_text: str) -> JSONFormatInfo:
    newline = "\r\n" if "\r\n" in raw_text else "\n"
    had_trailing = raw_text.endswith("\n") or raw_text.endswith("\r\n")
    
    # Try detecting indent
    indent = 2
    for line in raw_text.splitlines():
        if line.startswith("    "):
            indent = 4
            break
        elif line.startswith("  "):
            indent = 2
            break
    return JSONFormatInfo(indent=indent, newline=newline, had_trailing_newline=had_trailing)

def read_json(path: Path) -> Tuple[Dict[str, Any], JSONFormatInfo]:
    if not path.exists():
        return {}, JSONFormatInfo()
    
    with open(path, "r", encoding="utf-8") as fp:
        raw = fp.read()
    
    fmt = detect_format(raw)
    stripped = raw.strip()
    if not stripped:
        return {}, fmt
    
    data = json.loads(stripped)
    if not isinstance(data, dict):
        raise ValueError(f"Root of JSON at {path} must be an object (dict)")
    return data, fmt

def write_json_atomic(path: Path, data: Dict[str, Any], fmt: Optional[JSONFormatInfo] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = fmt or JSONFormatInfo()
    
    encoded = json.dumps(data, indent=fmt.indent, ensure_ascii=False)
    if fmt.newline != "\n":
        encoded = encoded.replace("\n", fmt.newline)
    if fmt.had_trailing_newline and not encoded.endswith(fmt.newline):
        encoded += fmt.newline

    # Write to temp file in same directory for atomic replace
    tmp_path = path.parent / f".tmp_{path.name}_{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as fp:
        fp.write(encoded)
        fp.flush()
        os.fsync(fp.fileno())

    # Readback check before committing!
    with open(tmp_path, "r", encoding="utf-8") as fp:
        readback = json.load(fp)
    if not isinstance(readback, dict):
        raise ValueError("Sanity check failed: written file is not a valid JSON dictionary")

    # Atomic replace
    os.replace(tmp_path, path)
