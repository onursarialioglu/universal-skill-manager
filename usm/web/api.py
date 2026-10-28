from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from usm.core.service import USMService
from usm.core.templates import list_templates
from usm.models import Skill, TargetBinding, Transport

router = APIRouter(prefix="/api")

def get_svc() -> USMService:
    return USMService()

class SkillCreateRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    kind: str = "mcp_server"
    content: Optional[str] = None
    scope: str = "auto"
    transport: str = "stdio"
    command: Optional[str] = None
    args: List[str] = []
    env: Dict[str, str] = {}
    url: Optional[str] = None
    targets: List[str] = []

@router.get("/status")
def get_status():
    svc = get_svc()
    reports = svc.get_clients_status()
    return [
        {
            "client_id": r.client_id,
            "status": r.status.value,
            "path": str(r.path) if r.path else None,
            "candidates_count": len(r.candidates)
        }
        for r in reports
    ]

@router.get("/skills")
def get_skills():
    svc = get_svc()
    skills = svc.list_skills()
    health = {h.skill_id: h.model_dump() for h in svc.check_health()}
    return [
        {
            **s.model_dump(mode="json"),
            "health": health.get(s.id, {"status": "unknown"})
        }
        for s in skills
    ]

@router.post("/skills")
def create_skill(req: SkillCreateRequest):
    svc = get_svc()
    targets_binding = "all" if not req.targets else [TargetBinding(client_id=cid) for cid in req.targets]
    skill = Skill(
        id=req.id,
        name=req.name,
        description=req.description,
        kind="agent_skill" if req.kind == "agent_skill" else "mcp_server",
        content=req.content,
        scope=req.scope if req.scope in ("workspace", "global", "auto") else "auto",
        transport=Transport(req.transport) if req.kind != "agent_skill" else Transport.STDIO,
        command=req.command,
        args=req.args,
        env=req.env,
        url=req.url,
        targets=targets_binding
    )
    tx = svc.add_skill(skill, auto_sync=True)
    return {"status": "ok", "skill_id": skill.id, "kind": skill.kind, "tx_id": tx.id if tx else None}

@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: str):
    svc = get_svc()
    tx = svc.remove_skill(skill_id, auto_sync=True)
    return {"status": "ok", "deleted": True, "tx_id": tx.id if tx else None}

@router.post("/sync")
def trigger_sync():
    svc = get_svc()
    plan = svc.build_plan(trigger="web:sync")
    tx = svc.apply_plan(plan)
    return {
        "status": "ok",
        "tx_id": tx.id,
        "tx_status": tx.status,
        "steps_count": len(tx.steps)
    }

@router.get("/history")
def get_history():
    svc = get_svc()
    txs = svc.journal_mgr.list_transactions()
    return [t.model_dump(mode="json") for t in txs[:20]]

@router.post("/undo")
def trigger_undo(tx_id: Optional[str] = None):
    svc = get_svc()
    success = svc.undo_transaction(tx_id)
    return {"status": "ok" if success else "failed"}

@router.get("/templates")
def get_templates():
    return [t.model_dump(mode="json") for t in list_templates()]

@router.get("/settings")
def get_settings():
    svc = get_svc()
    return svc.get_settings().model_dump(mode="json")

@router.put("/settings")
def update_settings(data: Dict[str, Any]):
    from usm.settings import Settings
    svc = get_svc()
    current = svc.get_settings().model_dump()
    current.update(data)
    new_settings = Settings.model_validate(current)
    svc.update_settings(new_settings)
    return {"status": "ok", "settings": new_settings.model_dump(mode="json")}

