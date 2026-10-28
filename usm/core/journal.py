import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from usm.models import Transaction, TxStep
from usm.settings import get_usm_home

class JournalManager:
    def __init__(self):
        self.journal_dir = get_usm_home() / "journal"
        self.journal_dir.mkdir(parents=True, exist_ok=True)

    def _get_current_log_path(self) -> Path:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        return self.journal_dir / f"{month}.jsonl"

    def record_transaction(self, tx: Transaction) -> None:
        log_file = self._get_current_log_path()
        with open(log_file, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(tx.model_dump(mode="json"), ensure_ascii=False) + "\n")

    def list_transactions(self) -> List[Transaction]:
        transactions = []
        for file in sorted(self.journal_dir.glob("*.jsonl"), reverse=True):
            with open(file, "r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            transactions.append(Transaction.model_validate(data))
                        except Exception:
                            pass
        return transactions

    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        for tx in self.list_transactions():
            if tx.id == tx_id:
                return tx
        return None
