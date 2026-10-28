from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class Transport(str, Enum):
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


class Runner(str, Enum):
    NPX = "npx"
    UVX = "uvx"
    DOCKER = "docker"
    PYTHON = "python"
    NODE = "node"
    BINARY = "binary"
    CUSTOM = "custom"


class EnvValue(BaseModel):
    value: Optional[str] = None
    secret: Optional[str] = None
    required: bool = True
    description: Optional[str] = None


class PlatformOverride(BaseModel):
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, EnvValue]] = None


class TargetBinding(BaseModel):
    client_id: str
    enabled: bool = True
    native_extras: Dict[str, Any] = Field(default_factory=dict)
    name_override: Optional[str] = None


class Skill(BaseModel):
    id: str
    name: str
    description: str = ""
    kind: Literal["mcp_server", "agent_skill"] = "mcp_server"
    transport: Transport = Transport.STDIO
    runner: Runner = Runner.CUSTOM
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, Union[str, EnvValue]] = Field(default_factory=dict)
    cwd: Optional[str] = None
    url: Optional[str] = None
    headers: Dict[str, Union[str, EnvValue]] = Field(default_factory=dict)
    targets: Union[List[TargetBinding], Literal["all"]] = "all"
    platforms: Dict[str, PlatformOverride] = Field(default_factory=dict)
    enabled: bool = True
    tags: List[str] = Field(default_factory=list)
    content: Optional[str] = None
    scope: Literal["workspace", "global", "auto"] = "auto"
    source: str = "manual"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Registry(BaseModel):
    schema_version: int = 1
    skills: Dict[str, Skill] = Field(default_factory=dict)


class OpKind(str, Enum):
    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"
    ADOPT = "adopt"
    NOOP = "noop"
    SKIP = "skip"
    CONFLICT = "conflict"


class PlannedOp(BaseModel):
    client_id: str
    server_name: str
    kind: OpKind
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    reason_key: str
    risk: Literal["low", "medium", "high"] = "low"
    message: Optional[str] = None


class FileFingerprint(BaseModel):
    mtime: float
    size: int
    sha256: str


class ClientPlan(BaseModel):
    client_id: str
    config_path: Path
    fingerprint: Optional[FileFingerprint] = None
    ops: List[PlannedOp] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class Plan(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trigger: str = "cli:sync"
    clients: List[ClientPlan] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)


class TxStep(BaseModel):
    name: str
    client_id: Optional[str] = None
    status: Literal["ok", "failed", "skipped"]
    detail: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: int = 0


class Transaction(BaseModel):
    id: str
    plan_id: str
    status: Literal["applied", "partially_applied", "rolled_back", "failed"]
    steps: List[TxStep] = Field(default_factory=list)
    backups: Dict[str, str] = Field(default_factory=dict)
    undone_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ManagedEntry(BaseModel):
    native_name: str
    content_hash: str
    rendered: Dict[str, Any] = Field(default_factory=dict)
    written_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tx_id: str = ""


class ClientState(BaseModel):
    schema_version: int = 1
    client_id: str
    config_path: str
    managed: Dict[str, ManagedEntry] = Field(default_factory=dict)
    last_sync: Optional[datetime] = None
