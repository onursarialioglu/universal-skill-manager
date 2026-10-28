from typing import Any, Dict, List, Tuple
from usm.models import ManagedEntry, OpKind, PlannedOp
from usm.utils import compute_json_hash

def compute_3way_merge(
    client_id: str,
    base: Dict[str, ManagedEntry],
    local: Dict[str, Dict[str, Any]],
    desired: Dict[str, Dict[str, Any]],
    normalize_fn: Any = None
) -> Tuple[List[PlannedOp], Dict[str, Dict[str, Any]]]:
    """Computes planned operations and the merged servers dictionary."""
    ops: List[PlannedOp] = []
    final_servers: Dict[str, Dict[str, Any]] = dict(local)

    norm = normalize_fn or (lambda x: x)

    # 1. Evaluate servers in desired
    for name, des_val in desired.items():
        des_hash = compute_json_hash(norm(des_val))
        
        if name not in local:
            if name in base:
                # User deleted locally outside USM
                ops.append(PlannedOp(
                    client_id=client_id,
                    server_name=name,
                    kind=OpKind.ADD,
                    before=None,
                    after=des_val,
                    reason_key="plan.reason.readd",
                    risk="medium",
                    message="Server was deleted locally; re-adding per central registry."
                ))
                final_servers[name] = des_val
            else:
                # Completely new server target
                ops.append(PlannedOp(
                    client_id=client_id,
                    server_name=name,
                    kind=OpKind.ADD,
                    before=None,
                    after=des_val,
                    reason_key="plan.reason.new_target",
                    risk="low"
                ))
                final_servers[name] = des_val

        else:
            # Server exists in local
            loc_val = local[name]
            loc_hash = compute_json_hash(norm(loc_val))

            if name not in base:
                # Existed in local, not tracked by USM
                if loc_hash == des_hash:
                    ops.append(PlannedOp(
                        client_id=client_id,
                        server_name=name,
                        kind=OpKind.ADOPT,
                        before=loc_val,
                        after=des_val,
                        reason_key="plan.reason.adopt",
                        risk="low",
                        message="Identical local configuration adopted into USM ownership."
                    ))
                    final_servers[name] = des_val
                else:
                    ops.append(PlannedOp(
                        client_id=client_id,
                        server_name=name,
                        kind=OpKind.CONFLICT,
                        before=loc_val,
                        after=des_val,
                        reason_key="plan.reason.conflict",
                        risk="high",
                        message="Local server exists with different parameters. Overwrite required."
                    ))
                    # Keep local until user resolves conflict, or overwrite if requested
                    final_servers[name] = des_val
            else:
                # Existed in base
                base_entry = base[name]
                if loc_hash == base_entry.content_hash:
                    # User did not modify locally
                    if des_hash != base_entry.content_hash:
                        ops.append(PlannedOp(
                            client_id=client_id,
                            server_name=name,
                            kind=OpKind.UPDATE,
                            before=loc_val,
                            after=des_val,
                            reason_key="plan.reason.update",
                            risk="low"
                        ))
                        final_servers[name] = des_val
                    else:
                        ops.append(PlannedOp(
                            client_id=client_id,
                            server_name=name,
                            kind=OpKind.NOOP,
                            before=loc_val,
                            after=des_val,
                            reason_key="plan.reason.noop",
                            risk="low"
                        ))
                else:
                    # User modified locally (drift)
                    if des_hash == base_entry.content_hash:
                        # Desired hasn't changed, local changed
                        ops.append(PlannedOp(
                            client_id=client_id,
                            server_name=name,
                            kind=OpKind.NOOP,
                            before=loc_val,
                            after=des_val,
                            reason_key="plan.reason.drift",
                            risk="medium",
                            message="Local modification detected (drift). Retaining local state."
                        ))
                    else:
                        ops.append(PlannedOp(
                            client_id=client_id,
                            server_name=name,
                            kind=OpKind.CONFLICT,
                            before=loc_val,
                            after=des_val,
                            reason_key="plan.reason.conflict",
                            risk="high",
                            message="Both central registry and local config have conflicting modifications."
                        ))
                        final_servers[name] = des_val

    # 2. Evaluate servers in local not in desired
    for name, loc_val in local.items():
        if name not in desired:
            if name in base:
                # USM previously added it, now untargeted or removed
                ops.append(PlannedOp(
                    client_id=client_id,
                    server_name=name,
                    kind=OpKind.REMOVE,
                    before=loc_val,
                    after=None,
                    reason_key="plan.reason.remove",
                    risk="low"
                ))
                final_servers.pop(name, None)
            else:
                # Unmanaged user server: NEVER touch!
                pass

    return ops, final_servers
