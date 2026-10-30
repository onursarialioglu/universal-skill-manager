import glob
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import psutil

from usm.adapters import get_all_adapters
from usm.settings import ClientSetting, Settings, load_settings, save_settings

class DiscoveredApp(BaseModel):
    id: str
    name: str
    category: str  # "managed_client", "mcp_client", "ai_runtime", "consumer_shell"
    installed: bool
    running: bool
    path: Optional[str] = None
    managed: bool
    mcp_capable: bool
    recommendation: str

class AIScanner:
    """Intelligent discovery engine for finding AI clients, runtimes, and editors on the host machine."""

    KNOWN_EXTERNAL_APPS: List[Dict[str, Any]] = [
        {
            "id": "gemini-desktop",
            "name": "Google Gemini Desktop",
            "category": "consumer_shell",
            "mcp_capable": False,
            "detect_paths": [
                r"%LOCALAPPDATA%\Google\Gemini\Gemini.exe",
                r"%APPDATA%\gemini\settings.json",
            ],
            "process_names": ["gemini.exe"],
            "recommendation": "Consumer web-shell without local MCP file support. Use Google Antigravity to run Gemini models with USM.",
        },
        {
            "id": "deepseek-harness",
            "name": "DeepSeek Harness (DSH)",
            "category": "mcp_client",
            "mcp_capable": True,
            "detect_paths": [
                r"~/.dsh",
                r"%USERPROFILE%\.dsh",
            ],
            "process_names": ["dsh.exe", "dsh"],
            "recommendation": "DeepSeek agent harness detected. Privacy notice: set DSH_TELEMETRY_MODE=DISABLED to prevent remote log export.",
        },
        {
            "id": "continue",
            "name": "Continue.dev",
            "category": "mcp_client",
            "mcp_capable": True,
            "detect_paths": [
                r"~/.continue/config.json",
                r"~/.continue/config.yaml",
            ],
            "process_names": [],
            "syntax": "json",
            "root_key": "mcpServers",
            "recommendation": "MCP ready! Run 'usm register-client continue --config-path ~/.continue/config.json' to connect.",
        },
        {
            "id": "lm-studio",
            "name": "LM Studio",
            "category": "ai_runtime",
            "mcp_capable": True,
            "detect_paths": [
                r"%USERPROFILE%\.lmstudio",
                r"~/.cache/lm-studio",
            ],
            "process_names": ["lm studio.exe", "lmstudio.exe", "lmstudio"],
            "recommendation": "Local LLM runtime. Can connect to USM tools via standard MCP server proxies.",
        },
        {
            "id": "ollama",
            "name": "Ollama",
            "category": "ai_runtime",
            "mcp_capable": False,
            "detect_paths": [
                r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe",
                r"~/.ollama",
            ],
            "process_names": ["ollama.exe", "ollama app.exe", "ollama"],
            "recommendation": "Local model runner detected. Run 'ollama run <model>' with USM MCP tools.",
        },
        {
            "id": "zed",
            "name": "Zed Editor",
            "category": "mcp_client",
            "mcp_capable": True,
            "detect_paths": [
                r"%APPDATA%\Zed\settings.json",
                r"~/.config/zed/settings.json",
            ],
            "process_names": ["zed.exe", "zed"],
            "syntax": "json",
            "root_key": "context_servers",
            "recommendation": "Zed supports MCP context servers. Connect using 'usm register-client zed --config-path <path> --root-key context_servers'.",
        },
        {
            "id": "chatbox",
            "name": "Chatbox",
            "category": "consumer_shell",
            "mcp_capable": True,
            "detect_paths": [
                r"%APPDATA%\xyz.chatboxapp.chatbox",
                r"~/.chatbox",
            ],
            "process_names": ["chatbox.exe"],
            "recommendation": "Desktop AI chat client detected.",
        },
        {
            "id": "jan",
            "name": "Jan.ai",
            "category": "ai_runtime",
            "mcp_capable": True,
            "detect_paths": [
                r"%APPDATA%\jan",
                r"~/.jan",
            ],
            "process_names": ["jan.exe", "jan"],
            "recommendation": "Open-source desktop AI detected.",
        },
        {
            "id": "aider",
            "name": "Aider Pair Programmer",
            "category": "mcp_client",
            "mcp_capable": False,
            "detect_paths": [
                r"~/.aider.conf.yml",
            ],
            "process_names": ["aider.exe", "aider"],
            "recommendation": "Command-line AI coding assistant detected.",
        },
    ]

    @staticmethod
    def _get_running_processes() -> set:
        names = set()
        try:
            for p in psutil.process_iter(["name"]):
                n = p.info.get("name")
                if n:
                    names.add(n.lower())
        except Exception:
            pass
        return names

    @staticmethod
    def _expand(path_str: str) -> Path:
        expanded = os.path.expandvars(path_str)
        if expanded.startswith("~"):
            expanded = str(Path.home()) + expanded[1:]
        return Path(expanded.replace("/", os.sep).replace("\\", os.sep))

    @classmethod
    def scan(cls, settings: Optional[Settings] = None) -> List[DiscoveredApp]:
        if settings is None:
            settings = load_settings()

        results: List[DiscoveredApp] = []
        running_procs = cls._get_running_processes()
        adapters = get_all_adapters()
        managed_ids = {a.id for a in adapters}

        # 1. Scan already configured/managed adapters
        for adapter in adapters:
            status = adapter.get_status(settings)
            is_running = False
            # Check candidate processes if profile-driven
            if hasattr(adapter, "profile") and hasattr(adapter.profile, "config"):
                for p in adapter.profile.config.process_names:
                    if p.lower() in running_procs:
                        is_running = True
                        break

            results.append(DiscoveredApp(
                id=adapter.id,
                name=getattr(adapter, "display_name_key", adapter.id),
                category="managed_client",
                installed=(status.status.value in ("ready", "installed_no_config")),
                running=is_running,
                path=str(status.path) if status.path else None,
                managed=True,
                mcp_capable=True,
                recommendation="Managed and synchronized by USM.",
            ))

        # 2. Scan known external AI tools
        for app in cls.KNOWN_EXTERNAL_APPS:
            if app["id"] in managed_ids:
                continue

            found_path = None
            for p_str in app["detect_paths"]:
                p = cls._expand(p_str)
                if p.exists():
                    found_path = p
                    break

            is_running = any(proc.lower() in running_procs for proc in app["process_names"])

            if found_path is not None or is_running:
                results.append(DiscoveredApp(
                    id=app["id"],
                    name=app["name"],
                    category=app["category"],
                    installed=(found_path is not None),
                    running=is_running,
                    path=str(found_path) if found_path else None,
                    managed=False,
                    mcp_capable=app.get("mcp_capable", False),
                    recommendation=app["recommendation"],
                ))

        return results

    @classmethod
    def auto_register_detected(cls, settings: Optional[Settings] = None) -> List[str]:
        """Auto-registers any detected external apps that have config files and are MCP capable."""
        if settings is None:
            settings = load_settings()

        apps = cls.scan(settings)
        registered: List[str] = []

        for app in apps:
            if not app.managed and app.installed and app.mcp_capable and app.path:
                # Find definition
                for defn in cls.KNOWN_EXTERNAL_APPS:
                    if defn["id"] == app.id and defn.get("root_key"):
                        settings.clients[app.id] = ClientSetting(
                            enabled=True,
                            path_override=app.path,
                            display_name=app.name,
                            syntax=defn.get("syntax", "json"),
                            root_key=defn.get("root_key", "mcpServers"),
                            custom=True,
                        )
                        registered.append(app.id)
                        break

        if registered:
            save_settings(settings)

        return registered
