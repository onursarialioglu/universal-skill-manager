import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from usm.adapters.base import BaseAdapter, ClientStatus, ClientStatusReport
from usm.models import Skill, TargetBinding, Transport
from usm.settings import ClientSetting, Settings

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        import tomllib  # type: ignore

class DynamicClientAdapter(BaseAdapter):
    """Universal adapter dynamically instantiated for user-registered or discovered AI clients."""

    def __init__(self, client_id: str, setting: ClientSetting):
        self.id = client_id
        self.setting = setting
        self.display_name_key = setting.display_name or f"client.{client_id}"
        self.syntax = setting.syntax or "json"
        self.root_key = setting.root_key or "mcpServers"

    def locate_config(self, settings: Settings) -> Optional[Path]:
        client_setting = settings.clients.get(self.id, self.setting)
        if client_setting and client_setting.path_override:
            p = Path(os.path.expandvars(client_setting.path_override)).expanduser().resolve()
            return p
        return None

    def get_status(self, settings: Settings) -> ClientStatusReport:
        client_setting = settings.clients.get(self.id, self.setting)
        if client_setting and not client_setting.enabled:
            return ClientStatusReport(self.id, ClientStatus.DISABLED)

        config_path = self.locate_config(settings)
        if not config_path:
            return ClientStatusReport(self.id, ClientStatus.NOT_INSTALLED)

        if config_path.exists():
            return ClientStatusReport(self.id, ClientStatus.READY, path=config_path)
        
        # If parent directory exists but config file not yet created
        if config_path.parent.exists():
            return ClientStatusReport(self.id, ClientStatus.INSTALLED_NO_CONFIG, path=config_path)

        return ClientStatusReport(self.id, ClientStatus.NOT_INSTALLED)

    def read_config(self, path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
        if self.syntax == "toml":
            if not path.exists():
                return {}, None
            try:
                with open(path, "rb") as fp:
                    return tomllib.load(fp), None
            except Exception as e:
                raise ValueError(f"Invalid TOML file at {path}: {e}") from e
        else:
            from usm.io.jsonio import read_json
            return read_json(path)

    def write_config(self, path: Path, raw: Dict[str, Any], fmt: Optional[str] = None) -> None:
        if self.syntax == "toml":
            path.parent.mkdir(parents=True, exist_ok=True)
            import tomli_w  # type: ignore
            temp_file = path.with_suffix(".tmp")
            with open(temp_file, "wb") as fp:
                tomli_w.dump(raw, fp)
            temp_file.replace(path)
        else:
            from usm.io.jsonio import write_json_atomic
            write_json_atomic(path, raw, fmt=fmt)

    def read_servers(self, raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        val = raw.get(self.root_key, {})
        if isinstance(val, dict):
            return dict(val)
        return {}

    def write_servers(self, raw: Dict[str, Any], servers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        updated = dict(raw)
        updated[self.root_key] = servers
        return updated

    def to_native(self, skill: Skill, binding: Optional[TargetBinding] = None) -> Dict[str, Any]:
        res: Dict[str, Any] = {}
        env_dict = {k: getattr(v, "value", str(v)) for k, v in skill.env.items()}

        if skill.transport == Transport.STDIO:
            cmd = skill.command or ""
            args = list(skill.args)
            if "windows" in skill.platforms and sys.platform == "win32":
                p_override = skill.platforms["windows"]
                if p_override.command:
                    cmd = p_override.command
                if p_override.args is not None:
                    args = list(p_override.args)

            res["command"] = cmd
            res["args"] = args
            if env_dict:
                res["env"] = env_dict

        elif skill.transport in (Transport.HTTP, Transport.SSE):
            res["url"] = skill.url or ""
            if env_dict:
                res["headers"] = env_dict

        if binding and binding.native_extras:
            res.update(binding.native_extras)

        return res

    def from_native(self, name: str, entry: Dict[str, Any]) -> Skill:
        if "url" in entry or "serverUrl" in entry:
            return Skill(
                id=name,
                name=name,
                transport=Transport.HTTP,
                url=entry.get("url") or entry.get("serverUrl"),
                headers=entry.get("headers", {}),
                source=f"import:{self.id}",
            )
        return Skill(
            id=name,
            name=name,
            transport=Transport.STDIO,
            command=entry.get("command", ""),
            args=entry.get("args", []),
            env=entry.get("env", {}),
            source=f"import:{self.id}",
        )
