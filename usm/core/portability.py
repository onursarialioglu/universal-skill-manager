import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from usm.models import Registry
from usm.registry import RegistryManager
from usm.settings import load_settings

class PortabilityManager:
    @staticmethod
    def export_profile(output_path: Path) -> Path:
        output_path = Path(output_path)
        if not output_path.name.endswith(".usmpack") and not output_path.name.endswith(".zip"):
            output_path = output_path.with_suffix(".usmpack")

        reg = RegistryManager().load()
        settings = load_settings()

        manifest = {
            "format_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "skill_count": len(reg.skills),
            "usm_version": "0.1.0"
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("skills.json", json.dumps(reg.model_dump(mode="json"), indent=2, ensure_ascii=False))
            zf.writestr("settings.json", json.dumps(settings.model_dump(mode="json"), indent=2, ensure_ascii=False))

        return output_path

    @staticmethod
    def import_profile(package_path: Path, overwrite: bool = False) -> int:
        package_path = Path(package_path)
        if not package_path.exists():
            raise FileNotFoundError(f"Package '{package_path}' not found.")

        with zipfile.ZipFile(package_path, "r") as zf:
            if "skills.json" not in zf.namelist():
                raise ValueError("Invalid USM package: missing skills.json")
            
            raw_skills = zf.read("skills.json").decode("utf-8")
            imported_reg = Registry.model_validate(json.loads(raw_skills))

        reg_mgr = RegistryManager()
        current_reg = reg_mgr.load()
        count = 0
        for skill_id, skill in imported_reg.skills.items():
            if skill_id not in current_reg.skills or overwrite:
                current_reg.skills[skill_id] = skill
                count += 1

        reg_mgr.save(current_reg)
        return count
