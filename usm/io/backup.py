import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from usm.settings import get_usm_home

class BackupManager:
    def __init__(self):
        self.central_dir = get_usm_home() / "backups"
        self.index_path = self.central_dir / "index.json"
        self.central_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> Dict[str, Any]:
        if not self.index_path.exists():
            return {"backups": []}
        try:
            with open(self.index_path, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:
            return {"backups": []}

    def _save_index(self, data: Dict[str, Any]) -> None:
        with open(self.index_path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2, ensure_ascii=False)

    def create_backup(self, config_path: Path, client_id: str, tx_id: str = "") -> Optional[Path]:
        if not config_path.exists():
            return None
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # 1. Local backup alongside the file: <filename>.bak_<timestamp>
        local_bak = config_path.parent / f"{config_path.name}.bak_{timestamp}"
        shutil.copy2(config_path, local_bak)

        # 2. Central backup directory
        client_central_dir = self.central_dir / client_id
        client_central_dir.mkdir(parents=True, exist_ok=True)
        central_bak = client_central_dir / f"{config_path.name}.bak_{timestamp}"
        shutil.copy2(config_path, central_bak)

        # Register in index
        idx = self._load_index()
        record = {
            "timestamp": timestamp,
            "client_id": client_id,
            "original_path": str(config_path),
            "local_backup": str(local_bak),
            "central_backup": str(central_bak),
            "tx_id": tx_id,
        }
        idx.setdefault("backups", []).append(record)
        self._save_index(idx)

        return local_bak

    def restore_backup(self, backup_path: Path, target_path: Path) -> bool:
        if not backup_path.exists():
            return False
        shutil.copy2(backup_path, target_path)
        return True

    def list_backups(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        idx = self._load_index()
        backups = idx.get("backups", [])
        if client_id:
            backups = [b for b in backups if b.get("client_id") == client_id]
        return backups
