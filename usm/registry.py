import json
from pathlib import Path
from typing import Dict, List, Optional
from usm.models import Registry, Skill
from usm.settings import get_usm_home

class RegistryManager:
    def __init__(self, registry_path: Optional[Path] = None):
        self.path = registry_path or (get_usm_home() / "skills.json")

    def load(self) -> Registry:
        if not self.path.exists():
            reg = Registry()
            self.save(reg)
            return reg
        try:
            with open(self.path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            return Registry.model_validate(data)
        except Exception:
            reg = Registry()
            self.save(reg)
            return reg

    def save(self, registry: Registry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # atomic write
        tmp_file = self.path.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as fp:
            json.dump(registry.model_dump(mode="json"), fp, indent=2, ensure_ascii=False)
        tmp_file.replace(self.path)

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        reg = self.load()
        return reg.skills.get(skill_id)

    def add_skill(self, skill: Skill) -> None:
        reg = self.load()
        reg.skills[skill.id] = skill
        self.save(reg)

    def remove_skill(self, skill_id: str) -> bool:
        reg = self.load()
        if skill_id in reg.skills:
            del reg.skills[skill_id]
            self.save(reg)
            return True
        return False

    def list_skills(self) -> List[Skill]:
        reg = self.load()
        return list(reg.skills.values())
