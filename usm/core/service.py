from pathlib import Path
from typing import Any, Dict, List, Optional
from usm.adapters import get_all_adapters, get_adapter
from usm.adapters.base import BaseAdapter, ClientStatusReport
from usm.core.engine import ApplyEngine
from usm.core.health import HealthChecker, HealthCheckResult
from usm.core.journal import JournalManager
from usm.core.planner import Planner
from usm.core.portability import PortabilityManager
from usm.io.backup import BackupManager
from usm.models import Plan, Registry, Skill, Transaction
from usm.registry import RegistryManager
from usm.settings import Settings, load_settings, save_settings

class USMService:
    def __init__(self):
        self.registry_mgr = RegistryManager()
        self.settings = load_settings()
        self.backup_mgr = BackupManager()
        self.journal_mgr = JournalManager()
        self.engine = ApplyEngine()

    def get_settings(self) -> Settings:
        return self.settings

    def update_settings(self, settings: Settings) -> None:
        self.settings = settings
        save_settings(settings)

    def list_skills(self) -> List[Skill]:
        return self.registry_mgr.list_skills()

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self.registry_mgr.get_skill(skill_id)

    def add_skill(self, skill: Skill, auto_sync: bool = True) -> Optional[Transaction]:
        self.registry_mgr.add_skill(skill)
        if skill.kind == "agent_skill":
            from usm.core.prompt_engine import PromptSkillDeployer
            PromptSkillDeployer.deploy_skill(skill)

        if auto_sync:
            plan = self.build_plan(trigger="cli:add")
            return self.apply_plan(plan)
        return None

    def remove_skill(self, skill_id: str, auto_sync: bool = True) -> Optional[Transaction]:
        skill = self.get_skill(skill_id)
        if skill and skill.kind == "agent_skill":
            from usm.core.prompt_engine import PromptSkillDeployer
            PromptSkillDeployer.remove_skill(skill_id)

        removed = self.registry_mgr.remove_skill(skill_id)
        if removed and auto_sync:
            plan = self.build_plan(trigger="cli:remove")
            return self.apply_plan(plan)
        return None

    def get_clients_status(self) -> List[ClientStatusReport]:
        adapters = get_all_adapters()
        reports = []
        for adapter in adapters:
            reports.append(adapter.get_status(self.settings))
        return reports

    def build_plan(self, target_client: Optional[str] = None, trigger: str = "cli:sync") -> Plan:
        registry = self.registry_mgr.load()
        planner = Planner(registry, self.settings)
        return planner.build_plan(target_client=target_client, trigger=trigger)

    def apply_plan(self, plan: Plan, client_filter: Optional[List[str]] = None) -> Transaction:
        # Also deploy any enabled agent skills
        from usm.core.prompt_engine import PromptSkillDeployer
        for sk in self.list_skills():
            if sk.kind == "agent_skill" and sk.enabled:
                PromptSkillDeployer.deploy_skill(sk)

        return self.engine.apply(plan, client_filter=client_filter)

    def undo_transaction(self, tx_id: Optional[str] = None) -> bool:
        txs = self.journal_mgr.list_transactions()
        if not txs:
            return False
        
        target_tx = None
        if tx_id:
            for t in txs:
                if t.id == tx_id:
                    target_tx = t
                    break
        else:
            # Most recent
            target_tx = txs[0]

        if not target_tx or not target_tx.backups:
            return False

        # Restore all backups from this transaction
        for client_id, bak_str in target_tx.backups.items():
            bak_path = Path(bak_str)
            adapter = get_adapter(client_id)
            if adapter and bak_path.exists():
                cfg_path = adapter.locate_config(self.settings)
                if cfg_path:
                    self.backup_mgr.restore_backup(bak_path, cfg_path)

        return True

    def check_health(self, skill_id: Optional[str] = None) -> List[HealthCheckResult]:
        if skill_id:
            sk = self.get_skill(skill_id)
            if sk:
                return [HealthChecker.check_skill(sk)]
            return []
        
        skills = self.list_skills()
        return [HealthChecker.check_skill(sk) for sk in skills]

    def export_profile(self, output_path: Path) -> Path:
        return PortabilityManager.export_profile(output_path)

    def import_profile(self, package_path: Path, overwrite: bool = False) -> int:
        return PortabilityManager.import_profile(package_path, overwrite=overwrite)

    def scan_environment(self, auto_register: bool = False) -> List[Any]:
        from usm.core.scanner import AIScanner
        if auto_register:
            AIScanner.auto_register_detected(self.settings)
        return AIScanner.scan(self.settings)

    def register_client(
        self,
        client_id: str,
        name: str,
        config_path: str,
        root_key: str = "mcpServers",
        syntax: str = "json",
        skills_dir: Optional[str] = None
    ) -> bool:
        from usm.settings import ClientSetting
        normalized_id = client_id.lower().replace("_", "-")
        self.settings.clients[normalized_id] = ClientSetting(
            enabled=True,
            path_override=config_path,
            display_name=name,
            root_key=root_key,
            syntax=syntax,
            skills_dir=skills_dir,
            custom=True,
        )
        self.update_settings(self.settings)
        return True
