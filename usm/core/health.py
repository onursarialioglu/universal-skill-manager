import os
import shutil
import subprocess
from typing import Dict, List, Optional
from pydantic import BaseModel
from usm.models import Skill, Transport

class HealthCheckResult(BaseModel):
    skill_id: str
    status: str  # "healthy", "warning", "error"
    command_resolved: bool
    resolved_path: Optional[str] = None
    issues: List[str] = []

class HealthChecker:
    @staticmethod
    def check_skill(skill: Skill) -> HealthCheckResult:
        issues = []
        status = "healthy"
        resolved_path = None
        cmd_resolved = False

        if skill.kind == "agent_skill":
            if not skill.content:
                issues.append("Prompt skill has no content.")
                status = "error"
            return HealthCheckResult(
                skill_id=skill.id,
                status=status,
                command_resolved=True,
                resolved_path=None,
                issues=issues
            )

        if skill.transport == Transport.STDIO:
            cmd = skill.command
            if not cmd:
                issues.append("No command specified for stdio transport.")
                status = "error"
            else:
                resolved = shutil.which(cmd)
                if resolved:
                    cmd_resolved = True
                    resolved_path = resolved
                else:
                    cmd_resolved = False
                    status = "warning"
                    issues.append(f"Command '{cmd}' not found on system PATH.")

        elif skill.transport in (Transport.HTTP, Transport.SSE):
            cmd_resolved = True
            if not skill.url:
                issues.append("No URL specified for HTTP transport.")
                status = "error"

        return HealthCheckResult(
            skill_id=skill.id,
            status=status,
            command_resolved=cmd_resolved,
            resolved_path=resolved_path,
            issues=issues
        )
