import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from usm.adapters import get_adapter
from usm.core.journal import JournalManager
from usm.core.merge import compute_3way_merge
from usm.core.planner import load_client_state, save_client_state
from usm.core.verify import verify_write, VerificationError
from usm.io.backup import BackupManager
from usm.io.jsonio import read_json, write_json_atomic
from usm.io.lock import USMLock
from usm.models import ManagedEntry, OpKind, Plan, Transaction, TxStep
from usm.utils import compute_file_sha256, compute_json_hash

class ApplyEngine:
    def __init__(self):
        self.backup_mgr = BackupManager()
        self.journal_mgr = JournalManager()

    def apply(self, plan: Plan, client_filter: Optional[List[str]] = None) -> Transaction:
        tx_id = f"tx_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        steps: List[TxStep] = []
        backups: Dict[str, str] = {}
        overall_status = "applied"

        with USMLock():
            for c_plan in plan.clients:
                if client_filter and c_plan.client_id not in client_filter:
                    continue

                # Filter out pure NOOPs
                active_ops = [op for op in c_plan.ops if op.kind != OpKind.NOOP]
                if not active_ops:
                    continue

                adapter = get_adapter(c_plan.client_id)
                if not adapter:
                    continue

                config_path = c_plan.config_path
                t0 = time.time()

                # 1. Fingerprint check
                if config_path.exists() and c_plan.fingerprint:
                    current_sha = compute_file_sha256(config_path)
                    if current_sha != c_plan.fingerprint.sha256:
                        steps.append(TxStep(
                            name="fingerprint_check",
                            client_id=c_plan.client_id,
                            status="failed",
                            detail="File changed on disk after plan generation. Aborting write to prevent collision."
                        ))
                        overall_status = "partially_applied"
                        continue

                # 2. Backup
                bak_path = self.backup_mgr.create_backup(config_path, c_plan.client_id, tx_id=tx_id)
                if bak_path:
                    backups[c_plan.client_id] = str(bak_path)
                    steps.append(TxStep(
                        name="backup",
                        client_id=c_plan.client_id,
                        status="ok",
                        detail=f"Created backup at {bak_path.name}"
                    ))

                # 3. Read current raw config
                raw_config, fmt = adapter.read_config(config_path) if config_path.exists() else ({}, None)
                local_servers = adapter.read_servers(raw_config)
                base_state = load_client_state(c_plan.client_id)

                # Recompute desired servers to write
                desired_servers = {}
                for op in c_plan.ops:
                    if op.kind in (OpKind.ADD, OpKind.UPDATE, OpKind.ADOPT):
                        if op.after:
                            desired_servers[op.server_name] = op.after

                _, final_servers = compute_3way_merge(
                    client_id=c_plan.client_id,
                    base=base_state,
                    local=local_servers,
                    desired=desired_servers,
                    normalize_fn=adapter.normalize
                )

                # 4. Atomic write
                new_raw = adapter.write_servers(raw_config, final_servers)
                try:
                    adapter.write_config(config_path, new_raw, fmt=fmt)
                    steps.append(TxStep(
                        name="write",
                        client_id=c_plan.client_id,
                        status="ok",
                        detail="Atomic write completed"
                    ))

                    # 5. Post-write verification
                    verify_write(
                        adapter=adapter,
                        config_path=config_path,
                        ops=active_ops,
                        before_raw=raw_config,
                        after_raw=new_raw
                    )
                    steps.append(TxStep(
                        name="verify",
                        client_id=c_plan.client_id,
                        status="ok",
                        detail="All post-write invariants verified cleanly"
                    ))

                    # 6. Update client state
                    new_state = dict(base_state)
                    for op in active_ops:
                        if op.kind in (OpKind.ADD, OpKind.UPDATE, OpKind.ADOPT) and op.after:
                            new_state[op.server_name] = ManagedEntry(
                                native_name=op.server_name,
                                content_hash=compute_json_hash(adapter.normalize(op.after)),
                                rendered=op.after,
                                tx_id=tx_id
                            )
                        elif op.kind == OpKind.REMOVE:
                            new_state.pop(op.server_name, None)

                    save_client_state(c_plan.client_id, str(config_path), new_state)

                except Exception as e:
                    # Verification or write failure -> ROLLBACK!
                    steps.append(TxStep(
                        name="verify",
                        client_id=c_plan.client_id,
                        status="failed",
                        detail=f"Verification failure: {e}"
                    ))
                    if bak_path and bak_path.exists():
                        self.backup_mgr.restore_backup(bak_path, config_path)
                        steps.append(TxStep(
                            name="rollback",
                            client_id=c_plan.client_id,
                            status="ok",
                            detail=f"Safely restored original file from backup {bak_path.name}"
                        ))
                    overall_status = "rolled_back"

        tx = Transaction(
            id=tx_id,
            plan_id=plan.id,
            status=overall_status,
            steps=steps,
            backups=backups
        )
        self.journal_mgr.record_transaction(tx)
        return tx
