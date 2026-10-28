from abc import ABC, abstractmethod
from enum import Enum
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from usm.models import Skill, TargetBinding, Transport
from usm.compat.profile_model import ClientProfile, load_profile_from_toml
from usm.compat.discovery import DiscoveryEngine, Candidate
from usm.settings import Settings

class ClientStatus(str, Enum):
    NOT_INSTALLED = "not_installed"
    INSTALLED_NO_CONFIG = "installed_no_config"
    READY = "ready"
    READ_ONLY = "read_only"
    AMBIGUOUS = "ambiguous"
    UNKNOWN_FORMAT = "unknown_format"
    ERROR = "error"
    DISABLED = "disabled"

class ClientStatusReport:
    def __init__(self, client_id: str, status: ClientStatus, path: Optional[Path] = None,
                 managed_count: int = 0, unmanaged_count: int = 0, candidates: Optional[List[Candidate]] = None):
        self.client_id = client_id
        self.status = status
        self.path = path
        self.managed_count = managed_count
        self.unmanaged_count = unmanaged_count
        self.candidates = candidates or []

class BaseAdapter(ABC):
    id: str
    display_name_key: str

    @abstractmethod
    def locate_config(self, settings: Settings) -> Optional[Path]: ...

    @abstractmethod
    def get_status(self, settings: Settings) -> ClientStatusReport: ...

    @abstractmethod
    def read_servers(self, raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]: ...

    @abstractmethod
    def write_servers(self, raw: Dict[str, Any], servers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]: ...

    @abstractmethod
    def to_native(self, skill: Skill, binding: Optional[TargetBinding] = None) -> Dict[str, Any]: ...

    @abstractmethod
    def from_native(self, name: str, entry: Dict[str, Any]) -> Skill: ...

    def normalize(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize an entry for consistent hashing (e.g. ignore UI toggles or client metadata)."""
        clean = dict(entry)
        for key in ["disabled", "autoApprove", "alwaysAllow", "timeout", "inputs"]:
            clean.pop(key, None)
        return clean

    def read_config(self, path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
        from usm.io.jsonio import read_json
        return read_json(path)

    def write_config(self, path: Path, raw: Dict[str, Any], fmt: Optional[str] = None) -> None:
        from usm.io.jsonio import write_json_atomic
        write_json_atomic(path, raw, fmt=fmt)

class ProfileDrivenAdapter(BaseAdapter):
    def __init__(self, profile_path: Path):
        self.profile = load_profile_from_toml(profile_path)
        self.id = self.profile.id
        self.display_name_key = self.profile.display_name_key
        self.discovery = DiscoveryEngine(self.profile)

    def locate_config(self, settings: Settings) -> Optional[Path]:
        client_setting = settings.clients.get(self.id)
        override = client_setting.path_override if client_setting else None
        return self.discovery.resolve_best_path(override)

    def get_status(self, settings: Settings) -> ClientStatusReport:
        client_setting = settings.clients.get(self.id)
        if client_setting and not client_setting.enabled:
            return ClientStatusReport(self.id, ClientStatus.DISABLED)

        candidates = self.discovery.discover_candidates()
        config_path = self.locate_config(settings)

        if not candidates and not config_path:
            return ClientStatusReport(self.id, ClientStatus.NOT_INSTALLED)

        # Check for ambiguity: multiple existing target files
        existing_files = [c for c in candidates if c.path.exists()]
        if len(existing_files) > 1 and not (client_setting and client_setting.path_override):
            return ClientStatusReport(self.id, ClientStatus.AMBIGUOUS, path=existing_files[0].path, candidates=candidates)

        if config_path and config_path.exists():
            return ClientStatusReport(self.id, ClientStatus.READY, path=config_path, candidates=candidates)
        
        if config_path and not config_path.exists():
            return ClientStatusReport(self.id, ClientStatus.INSTALLED_NO_CONFIG, path=config_path, candidates=candidates)

        return ClientStatusReport(self.id, ClientStatus.NOT_INSTALLED, candidates=candidates)

    def read_servers(self, raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        fmt = self.profile.formats[0] if self.profile.formats else None
        root_key = fmt.root_key if fmt else "mcpServers"
        val = raw.get(root_key, {})
        if isinstance(val, dict):
            return dict(val)
        return {}

    def write_servers(self, raw: Dict[str, Any], servers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        fmt = self.profile.formats[0] if self.profile.formats else None
        root_key = fmt.root_key if fmt else "mcpServers"
        updated = dict(raw)
        updated[root_key] = servers
        return updated

    def to_native(self, skill: Skill, binding: Optional[TargetBinding] = None) -> Dict[str, Any]:
        fmt = self.profile.formats[0] if self.profile.formats else None
        res: Dict[str, Any] = {}

        # Handle environment variables
        env_dict = {}
        for k, v in skill.env.items():
            if hasattr(v, "value"):
                env_dict[k] = v.value or ""
            else:
                env_dict[k] = str(v)

        if skill.transport == Transport.STDIO:
            cmd = skill.command or ""
            args = list(skill.args)

            # Windows platform override check
            if "windows" in skill.platforms and sys.platform == "win32":
                p_override = skill.platforms["windows"]
                if p_override.command:
                    cmd = p_override.command
                if p_override.args is not None:
                    args = list(p_override.args)

            stdio_fields = fmt.stdio if fmt else None
            cmd_field = stdio_fields.command if stdio_fields else "command"
            args_field = stdio_fields.args if stdio_fields else "args"
            env_field = stdio_fields.env if stdio_fields else "env"

            res[cmd_field] = cmd
            res[args_field] = args
            if env_dict:
                res[env_field] = env_dict

        elif skill.transport in (Transport.HTTP, Transport.SSE):
            http_fields = fmt.http if fmt else None
            url_field = http_fields.url if http_fields else "url"
            headers_field = http_fields.headers if http_fields else "headers"
            type_field = http_fields.type_field if http_fields else "type"

            res[url_field] = skill.url or ""
            if env_dict:
                res[headers_field] = env_dict
            if type_field:
                type_val = "sse" if skill.transport == Transport.SSE else "http"
                if http_fields and type_val in http_fields.type_map:
                    type_val = http_fields.type_map[type_val]
                res[type_field] = type_val

        # Add native extras from binding (e.g. autoApprove)
        if binding and binding.native_extras:
            res.update(binding.native_extras)

        return res

    def from_native(self, name: str, entry: Dict[str, Any]) -> Skill:
        # Infer transport
        if "url" in entry or "serverUrl" in entry:
            url = entry.get("url") or entry.get("serverUrl")
            headers = entry.get("headers", {})
            return Skill(
                id=name,
                name=name,
                transport=Transport.HTTP,
                url=url,
                headers=headers,
                source=f"import:{self.id}",
            )
        else:
            cmd = entry.get("command", "")
            args = entry.get("args", [])
            env = entry.get("env", {})
            return Skill(
                id=name,
                name=name,
                transport=Transport.STDIO,
                command=cmd,
                args=args,
                env=env,
                source=f"import:{self.id}",
            )
