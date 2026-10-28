from typing import Dict, List, Optional
from usm.adapters.base import BaseAdapter
from usm.adapters.claude_desktop import ClaudeDesktopAdapter
from usm.adapters.claude_code import ClaudeCodeAdapter
from usm.adapters.vscode_native import VSCodeNativeAdapter
from usm.adapters.cline import ClineAdapter
from usm.adapters.roo_code import RooCodeAdapter
from usm.adapters.cursor import CursorAdapter
from usm.adapters.windsurf import WindsurfAdapter
from usm.adapters.antigravity import AntigravityAdapter
from usm.adapters.codex import CodexAdapter

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
    return [cls() for cls in _ADAPTER_CLASSES]

def get_adapter(client_id: str) -> Optional[BaseAdapter]:
    normalized_id = client_id.lower().replace("_", "-")
    for cls in _ADAPTER_CLASSES:
        adapter = cls()
        if adapter.id == normalized_id:
            return adapter
        if adapter.id == "codex" and normalized_id in ("chatgpt", "openai", "codex-chatgpt"):
            return adapter
    return None
