import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from usm.adapters.base import ProfileDrivenAdapter
from usm.models import PlatformOverride, Skill, TargetBinding, Transport

def format_single_server_toml(name: str, s: Dict[str, Any]) -> str:
    lines = [f"[mcp_servers.{name}]"]
    for k, v in s.items():
        if k in ("env", "tools"):
            continue
        if isinstance(v, str):
            clean_v = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k} = "{clean_v}"')
        elif isinstance(v, bool):
            lines.append(f'{k} = {"true" if v else "false"}')
        elif isinstance(v, list):
            formatted = []
            for item in v:
                clean_item = str(item).replace("\\", "\\\\").replace('"', '\\"')
                formatted.append(f'"{clean_item}"')
            lines.append(f"{k} = [{', '.join(formatted)}]")
        elif isinstance(v, (int, float)):
            lines.append(f'{k} = {v}')

    if "tools" in s and isinstance(s["tools"], dict):
        for t_name, t_val in s["tools"].items():
            lines.append(f"\n[mcp_servers.{name}.tools.{t_name}]")
            for tk, tv in t_val.items():
                if isinstance(tv, str):
                    lines.append(f'{tk} = "{tv}"')
                elif isinstance(tv, bool):
                    lines.append(f'{tk} = {"true" if tv else "false"}')
                else:
                    lines.append(f'{tk} = {tv}')

    if "env" in s and isinstance(s["env"], dict) and s["env"]:
        lines.append(f"\n[mcp_servers.{name}.env]")
        for ek, ev in s["env"].items():
            val = ev.value if hasattr(ev, "value") else str(ev)
            clean_val = str(val).replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{ek} = "{clean_val}"')

    return "\n".join(lines)

def update_toml_servers(orig_text: str, desired_servers: Dict[str, Dict[str, Any]]) -> str:
    lines = orig_text.splitlines()
    pre = []
    post = []
    existing_blocks: Dict[str, List[str]] = {}
    curr_server = None
    in_mcp = False
    seen_mcp = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[mcp_servers."):
            seen_mcp = True
            in_mcp = True
            parts = stripped[len("[mcp_servers."):].rstrip("]").split(".")
            s_name = parts[0]
            curr_server = s_name
            if s_name not in existing_blocks:
                existing_blocks[s_name] = []
            existing_blocks[s_name].append(line)
        elif stripped.startswith("[") and in_mcp:
            in_mcp = False
            curr_server = None
            post.append(line)
        elif in_mcp:
            if curr_server:
                existing_blocks[curr_server].append(line)
        else:
            if seen_mcp:
                post.append(line)
            else:
                pre.append(line)

    final_blocks: Dict[str, List[str]] = {}
    for s_name, s_data in desired_servers.items():
        if s_name in existing_blocks:
            final_blocks[s_name] = existing_blocks[s_name]
        else:
            formatted = format_single_server_toml(s_name, s_data)
            final_blocks[s_name] = formatted.splitlines()

    out_lines = list(pre)
    for s_name, b_lines in final_blocks.items():
        out_lines.extend(b_lines)
        out_lines.append("")
    out_lines.extend(post)

    return "\n".join(out_lines).rstrip() + "\n"

class CodexAdapter(ProfileDrivenAdapter):
    """Adapter for OpenAI Codex CLI and VS Code ChatGPT/Codex extension."""
    root_key = "mcp_servers"

    def __init__(self):
        profile_path = Path(__file__).parent.parent / "compat" / "profiles" / "codex.toml"
        super().__init__(profile_path)

    def read_config(self, path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
        if not path.exists():
            return {}, "toml"
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text)
        return data, "toml"

    def write_config(self, path: Path, raw: Dict[str, Any], fmt: Optional[str] = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        orig_text = path.read_text(encoding="utf-8") if path.exists() else ""
        servers = raw.get(self.root_key, {})
        final_text = update_toml_servers(orig_text, servers)

        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(final_text, encoding="utf-8")
        if path.exists():
            path.unlink()
        tmp_path.rename(path)
