import asyncio
import sys
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer

from usm.core.service import USMService
from usm.models import Skill, TargetBinding, Transport

def create_mcp_server() -> MCPServer:
    """Builds and configures the Universal Skill Manager MCP Server."""
    server = MCPServer(
        name="universal-skill-manager",
        description="Autonomous Cross-Client MCP Server & Prompt Skill Manager across Antigravity, Claude, Cursor, Windsurf, VS Code"
    )

    def get_svc() -> USMService:
        return USMService()

    @server.tool()
    def usm_status() -> Dict[str, Any]:
        """Check connection and detection status for all AI clients on this computer (Antigravity, Claude, Cursor, VS Code, Roo Code, etc.)."""
        svc = get_svc()
        reports = svc.get_clients_status()
        return {
            "clients": [
                {
                    "client_id": r.client_id,
                    "status": r.status.value,
                    "config_path": str(r.path) if r.path else None,
                    "candidates_count": len(r.candidates)
                }
                for r in reports
            ]
        }

    @server.tool()
    def usm_list_skills(kind: Optional[str] = None) -> Dict[str, Any]:
        """List all currently managed MCP servers and prompt skills across AI agent clients.
        
        Args:
            kind: Optional filter - 'mcp_server' (executable tools) or 'agent_skill' (prompt/rule skills).
        """
        svc = get_svc()
        skills = svc.list_skills()
        health = {h.skill_id: h.model_dump() for h in svc.check_health()}
        
        filtered = skills
        if kind:
            target_kind = "agent_skill" if kind in ("prompt", "agent_skill") else "mcp_server"
            filtered = [s for s in skills if s.kind == target_kind]

        return {
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "kind": s.kind,
                    "description": s.description,
                    "transport": s.transport.value,
                    "command": s.command,
                    "args": s.args,
                    "content_length": len(s.content or "") if s.kind == "agent_skill" else None,
                    "targets": s.targets if isinstance(s.targets, str) else [t.client_id for t in s.targets if t.enabled],
                    "health": health.get(s.id, {"status": "unknown"})
                }
                for s in filtered
            ]
        }

    @server.tool()
    def usm_add_mcp_server(
        id: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        description: str = "",
        targets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Register and synchronize a new executable MCP server (e.g. npx, uvx, python tool) across AI agent clients.
        
        Args:
            id: Unique identifier for the server (e.g. 'github', 'filesystem').
            command: Command runner (e.g. 'npx', 'uvx', 'python').
            args: Command line arguments list (e.g. ['-y', '@modelcontextprotocol/server-github']).
            env: Environment variables dictionary (e.g. {'GITHUB_TOKEN': 'ghp_...'}).
            description: Optional human-readable description of what the tool does.
            targets: List of client IDs to deploy to, or None/empty for all installed clients.
        """
        svc = get_svc()
        targets_binding = "all" if not targets else [TargetBinding(client_id=cid) for cid in targets]
        skill = Skill(
            id=id,
            name=id.capitalize(),
            description=description,
            kind="mcp_server",
            transport=Transport.STDIO,
            command=command,
            args=args or [],
            env=env or {},
            targets=targets_binding
        )
        tx = svc.add_skill(skill, auto_sync=True)
        return {
            "status": "success",
            "message": f"MCP server '{id}' registered and synchronized across targets.",
            "skill_id": id,
            "tx_id": tx.id if tx else None
        }

    @server.tool()
    def usm_add_prompt_skill(
        id: str,
        content: str,
        name: Optional[str] = None,
        description: str = "",
        scope: str = "auto",
        targets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Register and deploy a prompt/instruction skill (Markdown rules, coding standards, etc.) across AI agent clients.
        
        Args:
            id: Unique identifier for the skill (e.g. 'code-review-guidelines', 'fastapi-standards').
            content: The Markdown instruction text or prompt rules to be followed.
            name: Display name for the skill (defaults to capitalized ID).
            description: Short summary of what the rule/skill enforces.
            scope: Deployment scope - 'auto' (current workspace & global), 'workspace' (.agents/skills), or 'global'.
            targets: List of client IDs to deploy to, or None/empty for all agents.
        """
        svc = get_svc()
        targets_binding = "all" if not targets else [TargetBinding(client_id=cid) for cid in targets]
        skill = Skill(
            id=id,
            name=name or id.capitalize(),
            description=description,
            kind="agent_skill",
            content=content,
            scope=scope if scope in ("workspace", "global", "auto") else "auto",
            targets=targets_binding
        )
        tx = svc.add_skill(skill, auto_sync=True)
        return {
            "status": "success",
            "message": f"Prompt skill '{id}' created and deployed across target agent workspaces/configs.",
            "skill_id": id,
            "tx_id": tx.id if tx else None
        }

    @server.tool()
    def usm_remove_skill(id: str) -> Dict[str, Any]:
        """Remove an MCP server or prompt skill from the central registry and unlink it from all clients.
        
        Args:
            id: Identifier of the skill/server to remove.
        """
        svc = get_svc()
        tx = svc.remove_skill(id, auto_sync=True)
        return {
            "status": "success",
            "message": f"Skill '{id}' removed and unlinked from all clients.",
            "skill_id": id,
            "tx_id": tx.id if tx else None
        }

    @server.tool()
    def usm_sync_all(target_client: Optional[str] = None) -> Dict[str, Any]:
        """Perform a full synchronization across all detected AI agent configuration files with 3-way merge safety.
        
        Args:
            target_client: Optional client ID to sync specifically, or None to sync all clients.
        """
        svc = get_svc()
        plan = svc.build_plan(target_client=target_client, trigger="agent:sync")
        tx = svc.apply_plan(plan)
        return {
            "status": "success",
            "message": f"Synchronization completed across clients.",
            "tx_id": tx.id,
            "steps_count": len(tx.steps)
        }

    @server.tool()
    def usm_undo(tx_id: Optional[str] = None) -> Dict[str, Any]:
        """Undo/rollback configuration changes to the previous backup state.
        
        Args:
            tx_id: Specific transaction ID to rollback, or None for the most recent transaction.
        """
        svc = get_svc()
        success = svc.undo_transaction(tx_id)
        if success:
            return {"status": "success", "message": f"Transaction '{tx_id or 'latest'}' rolled back successfully."}
        return {"status": "error", "message": "Could not undo transaction (no backups found or transaction not found)."}

    return server

def run_mcp_server():
    """Runs the USM MCP server over stdio for AI agent interaction."""
    # Ensure UTF-8 on Windows console
    if sys.platform == "win32":
        try:
            sys.stdin.reconfigure(encoding="utf-8")
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    server = create_mcp_server()
    asyncio.run(server.run_stdio_async())

if __name__ == "__main__":
    run_mcp_server()
