from pathlib import Path
from typing import Dict, List, Optional
from usm.adapters.base import BaseAdapter, ProfileDrivenAdapter
from usm.adapters.claude_desktop import ClaudeDesktopAdapter
from usm.adapters.claude_code import ClaudeCodeAdapter
from usm.adapters.vscode_native import VSCodeNativeAdapter
from usm.adapters.cline import ClineAdapter
from usm.adapters.roo_code import RooCodeAdapter
from usm.adapters.cursor import CursorAdapter
from usm.adapters.windsurf import WindsurfAdapter
from usm.adapters.antigravity import AntigravityAdapter
from usm.adapters.codex import CodexAdapter
from usm.adapters.dynamic import DynamicClientAdapter
from usm.settings import get_usm_home, load_settings

_ADAPTER_CLASSES = [
    ClaudeDesktopAdapter,
    ClaudeCodeAdapter,
    VSCodeNativeAdapter,
    ClineAdapter,
    RooCodeAdapter,
    CursorAdapter,
    WindsurfAdapter,
    AntigravityAdapter,
    CodexAdapter,
]

def get_all_adapters() -> List[BaseAdapter]:
    adapters: List[BaseAdapter] = [cls() for cls in _ADAPTER_CLASSES]
    seen_ids = {a.id for a in adapters}

    # 1. Load user custom TOML profiles from ~/.skill-manager/profiles/
    profiles_dir = get_usm_home() / "profiles"
    if profiles_dir.exists():
        for toml_path in profiles_dir.glob("*.toml"):
            try:
                adp = ProfileDrivenAdapter(toml_path)
                if adp.id not in seen_ids:
                    adapters.append(adp)
                    seen_ids.add(adp.id)
            except Exception:
                pass

    # 2. Load dynamically registered custom clients from settings.json
    try:
        settings = load_settings()
        for cid, csetting in settings.clients.items():
            if csetting.custom and cid not in seen_ids:
                adapters.append(DynamicClientAdapter(cid, csetting))
                seen_ids.add(cid)
    except Exception:
        pass

    return adapters

def get_adapter(client_id: str) -> Optional[BaseAdapter]:
    normalized_id = client_id.lower().replace("_", "-")
    for adapter in get_all_adapters():
        if adapter.id == normalized_id:
            return adapter
        if adapter.id == "codex" and normalized_id in ("chatgpt", "openai", "codex-chatgpt"):
            return adapter
    return None
