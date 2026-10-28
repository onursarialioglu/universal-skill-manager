from pathlib import Path
from typing import Any, Dict, List
from usm.adapters.base import BaseAdapter
from usm.io.jsonio import read_json
from usm.models import OpKind, PlannedOp
from usm.utils import compute_json_hash

class VerificationError(Exception):
    pass

def verify_write(
    adapter: BaseAdapter,
    config_path: Path,
    ops: List[PlannedOp],
    before_raw: Dict[str, Any],
    after_raw: Dict[str, Any]
) -> None:
    # 1. Parse check: File on disk must parse cleanly
    try:
        on_disk_raw, _ = adapter.read_config(config_path)
    except Exception as e:
        raise VerificationError(f"Post-write verification failed: could not parse {config_path}: {e}")

    # 2. Rest intact check: Keys outside root MCP key must be identical
    fmt_root = getattr(adapter, "root_key", "mcpServers")
    if hasattr(adapter, "profile") and adapter.profile and adapter.profile.formats:
        fmt_root = adapter.profile.formats[0].root_key

    for k, v in before_raw.items():
        if k != fmt_root:
            if on_disk_raw.get(k) != v:
                raise VerificationError(f"Post-write verification failed: key outside MCP tree '{k}' was altered!")

    # 3. Readback check by adapter
    servers_on_disk = adapter.read_servers(on_disk_raw)
    servers_before = adapter.read_servers(before_raw)

    # 4. Unmanaged servers check
    managed_names = {op.server_name for op in ops}
    for name, s_val in servers_before.items():
        if name not in managed_names:
            if name not in servers_on_disk:
                raise VerificationError(f"CRITICAL: Unmanaged server '{name}' was removed during write!")
            if compute_json_hash(servers_on_disk[name]) != compute_json_hash(s_val):
                raise VerificationError(f"CRITICAL: Unmanaged server '{name}' was modified during write!")

    # 5. Ops reflected check
    for op in ops:
        if op.kind in (OpKind.ADD, OpKind.UPDATE, OpKind.ADOPT):
            if op.server_name not in servers_on_disk:
                raise VerificationError(f"Verification failed: expected server '{op.server_name}' to be present.")
        elif op.kind == OpKind.REMOVE:
            if op.server_name in servers_on_disk:
                raise VerificationError(f"Verification failed: expected server '{op.server_name}' to be removed.")
