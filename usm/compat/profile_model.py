import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        import tomllib  # type: ignore

class VariantDetect(BaseModel):
    path_exists: Optional[str] = None
    appx_package: Optional[str] = None
    bundle_id: Optional[str] = None
    process_exe_glob: Optional[str] = None
    any: Optional[List[Dict[str, Any]]] = None

class InstallVariant(BaseModel):
    name: str
    detect: Optional[VariantDetect] = None
    config_dir: str

class ConfigSettings(BaseModel):
    filename: str
    syntax: Literal["json", "jsonc", "toml"] = "json"
    process_names: List[str] = Field(default_factory=list)
    env_model: Literal["standard", "gui_minimal"] = "standard"
    restart_required: bool = True

class StdioFields(BaseModel):
    command: str = "command"
    args: str = "args"
    env: str = "env"

class HttpFields(BaseModel):
    url: str = "url"
    headers: str = "headers"
    type_field: Optional[str] = "type"
    type_map: Dict[str, str] = Field(default_factory=dict)

class FormatVersion(BaseModel):
    version: str = "v1"
    default: bool = True
    root_key: str = "mcpServers"
    transports: List[str] = Field(default_factory=lambda: ["stdio"])
    client_owned_fields: List[str] = Field(default_factory=list)
    stdio: StdioFields = Field(default_factory=StdioFields)
    http: Optional[HttpFields] = None

class KnownIssue(BaseModel):
    id: str
    severity: Literal["info", "warning", "error"] = "warning"
    message_key: str

class ClientProfile(BaseModel):
    id: str
    display_name_key: str
    install_variants: List[InstallVariant] = Field(default_factory=list)
    config: ConfigSettings
    formats: List[FormatVersion] = Field(default_factory=list)
    known_issues: List[KnownIssue] = Field(default_factory=list)

def load_profile_from_toml(path: Path) -> ClientProfile:
    with open(path, "rb") as fp:
        raw = tomllib.load(fp)
    
    # Flatten variants from OS tables if structured like install.windows.variants
    variants = []
    install_dict = raw.get("install", {})
    if sys.platform == "win32":
        os_key = "windows"
    elif sys.platform == "darwin":
        os_key = "macos"
    else:
        os_key = "linux"
        
    os_variants = install_dict.get(os_key, {}).get("variants", [])
    for v in os_variants:
        variants.append(InstallVariant(**v))

    config_data = raw.get("config", {})
    formats_list = []
    for f in raw.get("formats", []):
        fields = f.get("fields", {})
        stdio_fields = StdioFields(**fields.get("stdio", {}))
        http_data = fields.get("http")
        http_fields = HttpFields(**http_data) if http_data else None
        formats_list.append(FormatVersion(
            version=f.get("version", "v1"),
            default=f.get("default", True),
            root_key=f.get("root_key", "mcpServers"),
            transports=f.get("transports", ["stdio"]),
            client_owned_fields=f.get("client_owned_fields", []),
            stdio=stdio_fields,
            http=http_fields
        ))

    known_issues = [KnownIssue(**ki) for ki in raw.get("known_issues", [])]

    return ClientProfile(
        id=raw.get("id", path.stem),
        display_name_key=raw.get("display_name_key", f"client.{path.stem}"),
        install_variants=variants,
        config=ConfigSettings(**config_data),
        formats=formats_list,
        known_issues=known_issues,
    )
