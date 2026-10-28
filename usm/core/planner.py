import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from usm.adapters import get_all_adapters, get_adapter
from usm.adapters.base import BaseAdapter, ClientStatus
from usm.core.merge import compute_3way_merge
from usm.io.jsonio import read_json
from usm.models import ClientPlan, FileFingerprint, ManagedEntry, OpKind, Plan, Registry, Skill
from usm.settings import Settings, get_usm_home
from usm.utils import compute_file_sha256

def load_client_state(client_id: str) -> Dict[str, ManagedEntry]:
    state_file = get_usm_home() / "state" / f"{client_id}.json"
    if not state_file.exists():
        return {}
    try:
        with open(state_file, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        managed = data.get("managed", {})
        return {k: ManagedEntry.model_validate(v) for k, v in managed.items()}
    except Exception:
        return {}

def save_client_state(client_id: str, config_path: str, managed: Dict[str, ManagedEntry]) -> None:
    state_dir = get_usm_home() / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{client_id}.json"
    data = {
        "schema_version": 1,
        "client_id": client_id,
        "config_path": str(config_path),
        "managed": {k: v.model_dump(mode="json") for k, v in managed.items()},
        "last_sync": datetime.now(timezone.utc).isoformat()
    }
    with open(state_file, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)

class Planner:
    def __init__(self, registry: Registry, settings: Settings):
        self.registry = registry
        self.settings = settings

    def build_plan(self, target_client: Optional[str] = None, trigger: str = "cli:sync") -> Plan:
        plan_id = f"plan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        adapters = [get_adapter(target_client)] if target_client else get_all_adapters()
        adapters = [a for a in adapters if a is not None]

        client_plans: List[ClientPlan] = []
        summary: Dict[str, int] = {k.value: 0 for k in OpKind}

        for adapter in adapters:
            status_report = adapter.get_status(self.settings)
            if status_report.status not in (ClientStatus.READY, ClientStatus.INSTALLED_NO_CONFIG):
                continue
            
            config_path = status_report.path
            if not config_path:
                continue

            raw_config: Dict[str, Any] = {}
            fingerprint = None
            if config_path.exists():
                try:
                    raw_config, _ = adapter.read_config(config_path)
                    stat = config_path.stat()
                    fingerprint = FileFingerprint(
                        mtime=stat.st_mtime,
                        size=stat.st_size,
                        sha256=compute_file_sha256(config_path)
                    )
                except Exception as e:
                    # Parse error
                    continue

            local_servers = adapter.read_servers(raw_config)
            base_state = load_client_state(adapter.id)

            # Build desired servers for this client
            desired_servers: Dict[str, Dict[str, Any]] = {}
            for skill in self.registry.skills.values():
                if not skill.enabled or skill.kind == "agent_skill":
                    continue
                # Check target bindings
                is_targeted = False
                matched_binding = None
                if skill.targets == "all":
                    is_targeted = True
                elif isinstance(skill.targets, list):
                    for b in skill.targets:
                        if b.client_id == adapter.id and b.enabled:
                            is_targeted = True
                            matched_binding = b
                            break

                if is_targeted:
                    native_entry = adapter.to_native(skill, matched_binding)
                    server_name = matched_binding.name_override if (matched_binding and matched_binding.name_override) else skill.id
                    desired_servers[server_name] = native_entry

            ops, _ = compute_3way_merge(
                client_id=adapter.id,
                base=base_state,
                local=local_servers,
                desired=desired_servers,
                normalize_fn=adapter.normalize
            )

            for op in ops:
                summary[op.kind.value] = summary.get(op.kind.value, 0) + 1

            client_plans.append(ClientPlan(
                client_id=adapter.id,
                config_path=config_path,
                fingerprint=fingerprint,
                ops=ops
            ))

        return Plan(
            id=plan_id,
            trigger=trigger,
            clients=client_plans,
            summary=summary
        )
