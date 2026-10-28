import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone
import shutil

from usm.models import Skill, TargetBinding
from usm.settings import get_usm_home

SUPPORTED_PROMPT_CLIENTS: List[str] = [
    "antigravity",
    "codex",
    "claude_code",
    "claude_desktop",
    "cursor",
    "windsurf",
    "cline",
    "roo_code",
]

class PromptSkillDeployer:
    """Deploys and synchronizes prompt/instruction-based skills across AI agent clients."""

    @staticmethod
    def format_frontmatter(skill_id: str, description: str, content: str) -> str:
        """Formats markdown content with standard YAML frontmatter for agents."""
        clean_content = content.strip() if content else ""
        desc = description.replace('"', '\\"').strip() if description else skill_id
        return f"---\nname: {skill_id}\ndescription: \"{desc}\"\n---\n\n{clean_content}\n"

    @staticmethod
    def get_target_paths(skill_id: str, client_id: str, scope: str = "auto", base_dir: Optional[Path] = None) -> List[Path]:
        """Resolves target file paths for a client given scope and base directory."""
        root = base_dir or Path.cwd()
        home = Path.home()
        paths = []

        if client_id == "antigravity":
            # Global
            global_path = home / ".gemini" / "config" / "skills" / skill_id / "SKILL.md"
            # Workspace
            ws_path = root / ".agents" / "skills" / skill_id / "SKILL.md"

            if scope == "global":
                paths.append(global_path)
            elif scope == "workspace":
                paths.append(ws_path)
            else:  # auto: global so available everywhere, and workspace if working in a project
                paths.append(global_path)
                if root != home:
                    paths.append(ws_path)

        elif client_id in ("claude_code", "claude_desktop"):
            global_path = home / ".claude" / "skills" / skill_id / "SKILL.md"
            ws_path = root / ".claude" / "skills" / skill_id / "SKILL.md"
            if scope == "global":
                paths.append(global_path)
            elif scope == "workspace":
                paths.append(ws_path)
            else:  # auto
                paths.append(global_path)
                if root != home:
                    paths.append(ws_path)

        elif client_id == "cursor":
            paths.append(root / ".cursor" / "rules" / f"{skill_id}.mdc")

        elif client_id == "windsurf":
            paths.append(root / ".windsurf" / "rules" / f"{skill_id}.md")

        elif client_id in ("cline", "roo_code"):
            paths.append(root / ".clinerules" / f"{skill_id}.md")

        elif client_id in ("codex", "chatgpt", "openai"):
            global_path = home / ".codex" / "skills" / skill_id / "SKILL.md"
            ws_path = root / ".codex" / "skills" / skill_id / "SKILL.md"
            if scope == "global":
                paths.append(global_path)
            elif scope == "workspace":
                paths.append(ws_path)
            else:  # auto: global is primary so Codex Desktop & all sessions find it
                paths.append(global_path)
                if root != home:
                    paths.append(ws_path)

        return paths

    @classmethod
    def deploy_skill(
        cls,
        skill: Skill,
        target_clients: Optional[List[str]] = None,
        base_dir: Optional[Path] = None
    ) -> Dict[str, List[Path]]:
        """Deploys a prompt skill to all resolved target clients."""
        if skill.kind != "agent_skill" or not skill.content:
            return {}

        results: Dict[str, List[Path]] = {}
        rendered = cls.format_frontmatter(skill.id, skill.description, skill.content)

        # Determine target clients
        clients = []
        if skill.targets == "all":
            clients = list(SUPPORTED_PROMPT_CLIENTS)
        elif isinstance(skill.targets, list):
            clients = [t.client_id for t in skill.targets if t.enabled]
        
        if target_clients:
            clients = [c for c in clients if c in target_clients]

        backup_dir = get_usm_home() / "backups" / "prompt_skills"
        backup_dir.mkdir(parents=True, exist_ok=True)

        for client_id in clients:
            paths = cls.get_target_paths(skill.id, client_id, scope=skill.scope, base_dir=base_dir)
            deployed = []
            for p in paths:
                p.parent.mkdir(parents=True, exist_ok=True)
                # Create backup if exists
                if p.exists():
                    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                    bak_file = backup_dir / f"{skill.id}_{client_id}_{ts}.bak"
                    shutil.copy2(p, bak_file)

                # Atomic write
                temp_file = p.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(rendered)
                temp_file.replace(p)
                deployed.append(p)

            results[client_id] = deployed

        return results

    @classmethod
    def remove_skill(
        cls,
        skill_id: str,
        target_clients: Optional[List[str]] = None,
        base_dir: Optional[Path] = None
    ) -> Dict[str, List[Path]]:
        """Removes a deployed prompt skill from all target clients."""
        clients = target_clients or list(SUPPORTED_PROMPT_CLIENTS)
        removed: Dict[str, List[Path]] = {}

        for client_id in clients:
            # Check both workspace and global
            ws_paths = cls.get_target_paths(skill_id, client_id, scope="workspace", base_dir=base_dir)
            global_paths = cls.get_target_paths(skill_id, client_id, scope="global", base_dir=base_dir)
            all_paths = set(ws_paths + global_paths)

            removed_client_paths = []
            for p in all_paths:
                if p.exists():
                    p.unlink()
                    removed_client_paths.append(p)
                    # If parent folder is named skill_id and empty, remove parent
                    parent = p.parent
                    if parent.name == skill_id and not any(parent.iterdir()):
                        try:
                            parent.rmdir()
                        except OSError:
                            pass

            if removed_client_paths:
                removed[client_id] = removed_client_paths

        return removed
