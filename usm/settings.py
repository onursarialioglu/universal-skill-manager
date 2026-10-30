import json
import os
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field
import platformdirs

class ClientSetting(BaseModel):
    enabled: bool = True
    path_override: Optional[str] = None
    strategy: Literal["file", "cli"] = "file"
    display_name: Optional[str] = None
    config_filename: Optional[str] = None
    syntax: Literal["json", "toml"] = "json"
    root_key: str = "mcpServers"
    skills_dir: Optional[str] = None
    custom: bool = False

class UISettings(BaseModel):
    theme: Literal["dark", "light", "system"] = "system"
    port: int = 8765

class SyncSettings(BaseModel):
    on_external_delete: Literal["ask", "readd", "respect"] = "ask"
    on_drift: Literal["ask", "overwrite", "adopt_local", "ignore"] = "ask"

class BackupSettings(BaseModel):
    mirror_central: bool = True
    per_client_retention: int = 20
    retention_days: int = 30

class CompatSettings(BaseModel):
    allow_transforms: bool = True
    allow_bridges: Literal["ask", "never", "always"] = "ask"
    min_confidence: float = 0.7
    on_ambiguous: Literal["ask", "skip"] = "ask"
    on_unknown_format: Literal["read_only", "suggest_learn"] = "read_only"
    effective_verify: Literal["off", "after_restart"] = "off"
    updates_enabled: bool = False

class RuntimeSettings(BaseModel):
    path_strategy: Literal["auto", "absolute", "inject_path", "none"] = "auto"
    wrap_cmd_shims: Literal["auto", "always", "never"] = "auto"

class DaemonSettings(BaseModel):
    enabled: bool = False
    auto_sync: Literal["off", "notify", "auto"] = "notify"
    autostart: bool = False

class Settings(BaseModel):
    schema_version: int = 1
    language: str = "en"
    approval_mode: Literal["always_ask", "ask_on_risk", "auto"] = "always_ask"
    ui: UISettings = Field(default_factory=UISettings)
    sync: SyncSettings = Field(default_factory=SyncSettings)
    compat: CompatSettings = Field(default_factory=CompatSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    backup: BackupSettings = Field(default_factory=BackupSettings)
    clients: Dict[str, ClientSetting] = Field(default_factory=dict)
    daemon: DaemonSettings = Field(default_factory=DaemonSettings)
    restart_prompt: bool = True
    lock_timeout_seconds: int = 15
    log_level: str = "INFO"

def get_usm_home() -> Path:
    # 1. Check USM_HOME env var
    env_home = os.environ.get("USM_HOME")
    if env_home:
        p = Path(env_home).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    # 2. Portable mode: marker file near executable or cwd
    cwd = Path.cwd()
    if (cwd / "usm.portable").exists() or (cwd / ".usm-portable").exists():
        p = cwd / "usm-data"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # 3. Default: ~/.skill-manager
    p = Path.home() / ".skill-manager"
    p.mkdir(parents=True, exist_ok=True)
    return p

def load_settings() -> Settings:
    home = get_usm_home()
    settings_file = home / "settings.json"
    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            return Settings.model_validate(data)
        except Exception:
            pass
    settings = Settings()
    save_settings(settings)
    return settings

def save_settings(settings: Settings) -> None:
    home = get_usm_home()
    settings_file = home / "settings.json"
    with open(settings_file, "w", encoding="utf-8") as fp:
        json.dump(settings.model_dump(mode="json"), fp, indent=2, ensure_ascii=False)
