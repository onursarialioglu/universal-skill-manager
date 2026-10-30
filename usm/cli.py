import json
import shlex
import sys
from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from usm import __version__, __app_name__
from usm.core.service import USMService
from usm.core.templates import get_template, list_templates
from usm.i18n import get_language, set_language, t
from usm.models import OpKind, PlatformOverride, Runner, Skill, TargetBinding, Transport
from usm.settings import get_usm_home

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(
    name=__app_name__,
    help="Universal Skill Manager (USM) - Centrally manage MCP servers across AI clients.",
    no_args_is_help=True
)
console = Console(safe_box=True)

@app.command("init")
def init_cmd(
    lang: Optional[str] = typer.Option(None, "--lang", help="Interface language (tr/en)")
):
    """Detect installed AI clients on the machine, display their status, and initialize central config."""
    if lang:
        set_language(lang)
    
    svc = USMService()
    home = get_usm_home()
    console.print(Panel(t("cli.init.welcome", path=str(home)), title="Universal Skill Manager", border_style="green"))

    # Status check
    status_cmd()

@app.command("status")
def status_cmd(
    as_json: bool = typer.Option(False, "--json", help="Output results in clean JSON format for scripts and agents")
):
    """Check which agent configuration paths are valid and accessible on the local PC."""
    svc = USMService()
    reports = svc.get_clients_status()

    if as_json:
        data = [
            {
                "client_id": r.client_id,
                "status": r.status.value,
                "config_path": str(r.path) if r.path else None,
                "candidates_count": len(r.candidates)
            }
            for r in reports
        ]
        console.print_json(data=data)
        return

    table = Table(title=t("cli.status.title", default="AI Client Detection & Health Status"), border_style="cyan")
    table.add_column("Client", style="bold")
    table.add_column("Status")
    table.add_column("Configuration Path")

    for rep in reports:
        status_key = f"status.{rep.status.value}"
        status_text = t(status_key, default=rep.status.value)
        if rep.status.value == "ready":
            style = "[green][OK] " + status_text + "[/green]"
        elif rep.status.value in ("installed_no_config", "ambiguous"):
            style = "[yellow][!] " + status_text + "[/yellow]"
        else:
            style = "[dim][-] " + status_text + "[/dim]"

        p_str = str(rep.path) if rep.path else "-"
        table.add_row(rep.client_id, style, p_str)

    console.print(table)

@app.command("list")
def list_cmd(
    as_json: bool = typer.Option(False, "--json", help="Output results in clean JSON format for scripts and agents")
):
    """Print a Rich formatted table showing all installed skills, their active targets, and health status."""
    svc = USMService()
    skills = svc.list_skills()

    if as_json:
        health_results = {h.skill_id: h.model_dump() for h in svc.check_health()}
        data = [
            {
                **sk.model_dump(mode="json"),
                "health": health_results.get(sk.id, {"status": "unknown"})
            }
            for sk in skills
        ]
        console.print_json(data=data)
        return

    if not skills:
        console.print(f"[yellow]{t('cli.list.empty')}[/yellow]")
        return

    table = Table(title="Registered Skills & Tools", border_style="magenta")
    table.add_column("ID", style="bold cyan")
    table.add_column("Name")
    table.add_column("Kind")
    table.add_column("Command / Content")
    table.add_column("Targets")
    table.add_column("Health")

    health_results = {h.skill_id: h for h in svc.check_health()}

    for sk in skills:
        kind_label = "[magenta]Prompt[/magenta]" if sk.kind == "agent_skill" else "[cyan]MCP[/cyan]"
        if sk.kind == "agent_skill":
            cmd_str = f"[dim]Markdown ({len(sk.content or '')} chars)[/dim]"
        else:
            cmd_str = sk.command or (sk.url or "-")
            if sk.args:
                cmd_str += " " + " ".join(sk.args[:2])
                if len(sk.args) > 2:
                    cmd_str += "..."

        targets_str = "all"
        if isinstance(sk.targets, list):
            targets_str = ", ".join([b.client_id for b in sk.targets if b.enabled])

        h = health_results.get(sk.id)
        if sk.kind == "agent_skill":
            health_str = "[green]✔ OK[/green]"
        elif h and h.status == "healthy":
            health_str = "[green]✔ OK[/green]"
        elif h and h.status == "warning":
            health_str = "[yellow]⚠ Warning[/yellow]"
        else:
            health_str = "[red]✘ Error[/red]"

        table.add_row(sk.id, sk.name, kind_label, cmd_str, targets_str, health_str)

    console.print(table)

@app.command("add")
def add_cmd(
    name: str = typer.Argument(..., help="Skill / Server identifier"),
    cmd: Optional[str] = typer.Option(None, "--cmd", help="Command or executable (e.g. npx, uvx, python)"),
    args: Optional[str] = typer.Option("", "--args", help="Arguments string (e.g. '-y @modelcontextprotocol/server-github')"),
    env: Optional[List[str]] = typer.Option(None, "--env", help="Environment variables in KEY=VAL format"),
    targets: str = typer.Option("all", "--targets", help="Comma-separated target clients (e.g. 'all' or 'claude-desktop,antigravity')"),
    template: Optional[str] = typer.Option(None, "--template", help="Use a pre-defined template (e.g. 'github', 'fetch', 'filesystem')"),
    transport: str = typer.Option("stdio", "--transport", help="Transport mode: stdio or http"),
    url: Optional[str] = typer.Option(None, "--url", help="URL for HTTP/SSE transport"),
    kind: str = typer.Option("mcp", "--kind", "-k", help="Skill kind: 'mcp' (executable server) or 'prompt' (agent instruction skill)"),
    content: Optional[str] = typer.Option(None, "--content", help="Markdown content string for prompt skills"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Markdown file path for prompt skills"),
    desc: str = typer.Option("", "--desc", help="Short description of the skill"),
    as_json: bool = typer.Option(False, "--json", help="Output results in clean JSON format for scripts and agents"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview plan without writing changes")
):
    """Register a new skill/server and optionally sync across targets."""
    svc = USMService()

    target_bindings = "all"
    if targets != "all":
        client_ids = [t.strip() for t in targets.split(",") if t.strip()]
        target_bindings = [TargetBinding(client_id=cid) for cid in client_ids]

    if kind in ("prompt", "agent_skill"):
        prompt_text = content
        if file:
            if not file.exists():
                console.print(f"[red]Error: File not found: {file}[/red]")
                raise typer.Exit(code=1)
            prompt_text = file.read_text(encoding="utf-8")

        if not prompt_text:
            console.print("[red]Error: Either --content or --file is required for prompt skills.[/red]")
            raise typer.Exit(code=2)

        skill = Skill(
            id=name,
            name=name.capitalize(),
            description=desc,
            kind="agent_skill",
            content=prompt_text,
            targets=target_bindings
        )
    elif template:
        try:
            skill = get_template(template)
            skill.id = name
            skill.name = name.capitalize()
            skill.targets = target_bindings
        except KeyError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(code=1)
    else:
        if not cmd and transport == "stdio":
            console.print("[red]Error: --cmd is required for stdio transport unless using --template.[/red]")
            raise typer.Exit(code=2)

        parsed_args = shlex.split(args) if args else []
        env_dict = {}
        if env:
            for item in env:
                if "=" in item:
                    k, v = item.split("=", 1)
                    env_dict[k.strip()] = v.strip()

        skill = Skill(
            id=name,
            name=name.capitalize(),
            description=desc,
            kind="mcp_server",
            transport=Transport(transport),
            command=cmd,
            args=parsed_args,
            env=env_dict,
            url=url,
            targets=target_bindings
        )

        if sys.platform == "win32" and cmd in ("npx", "uvx"):
            skill.platforms["windows"] = PlatformOverride(
                command="cmd",
                args=["/c", cmd] + parsed_args
            )

    if dry_run:
        from usm.core.planner import Planner
        hypothetical_reg = svc.registry_mgr.load()
        hypothetical_reg.skills[skill.id] = skill
        planner = Planner(hypothetical_reg, svc.settings)
        plan = planner.build_plan(trigger="cli:add")
        if as_json:
            console.print_json(data=plan.model_dump(mode="json"))
        else:
            print_plan(plan)
        return

    tx = svc.add_skill(skill, auto_sync=True)
    if as_json:
        console.print_json(data={
            "status": "ok",
            "skill_id": skill.id,
            "kind": skill.kind,
            "tx_id": tx.id if tx else None
        })
        return

    console.print(f"[green]{t('cli.add.success', name=name, count=len(tx.steps) if tx else 0)}[/green]")
    if tx:
        console.print(f"[dim]Transaction ID: {tx.id} (Undo: 'usm undo {tx.id}')[/dim]")

@app.command("remove")
def remove_cmd(
    name: str = typer.Argument(..., help="Skill ID to remove"),
    as_json: bool = typer.Option(False, "--json", help="Output results in clean JSON format for scripts and agents"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview plan without deleting")
):
    """Remove a skill from the registry and decouple from targets."""
    svc = USMService()
    if dry_run:
        from usm.core.planner import Planner
        hypothetical_reg = svc.registry_mgr.load()
        hypothetical_reg.skills.pop(name, None)
        planner = Planner(hypothetical_reg, svc.settings)
        plan = planner.build_plan(trigger="cli:remove")
        if as_json:
            console.print_json(data=plan.model_dump(mode="json"))
        else:
            print_plan(plan)
        return

    tx = svc.remove_skill(name, auto_sync=True)
    if as_json:
        console.print_json(data={
            "status": "ok" if tx else "not_found",
            "skill_id": name,
            "tx_id": tx.id if tx else None
        })
        return

    if tx:
        console.print(f"[green]{t('cli.remove.success', name=name)}[/green]")
        console.print(f"[dim]Transaction ID: {tx.id}[/dim]")
    else:
        console.print(f"[yellow]{t('cli.remove.not_found', name=name)}[/yellow]")

@app.command("sync")
def sync_cmd(
    target: Optional[str] = typer.Option(None, "--target", help="Specific client ID to sync"),
    as_json: bool = typer.Option(False, "--json", help="Output results in clean JSON format for scripts and agents"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview operations without applying")
):
    """Re-sync the central registry across all detected agent config files."""
    svc = USMService()
    plan = svc.build_plan(target_client=target, trigger="cli:sync")

    if not as_json:
        console.print(f"[blue]{t('cli.sync.start')}[/blue]")
        print_plan(plan)

    active_ops_count = sum(len([op for op in cp.ops if op.kind != OpKind.NOOP]) for cp in plan.clients)
    if active_ops_count == 0:
        if as_json:
            console.print_json(data={"status": "ok", "message": "already_in_sync", "active_ops": 0})
        else:
            console.print(f"[green]{t('cli.sync.noop')}[/green]")
        return

    if dry_run:
        if as_json:
            console.print_json(data=plan.model_dump(mode="json"))
        return

    tx = svc.apply_plan(plan)
    if as_json:
        console.print_json(data={
            "status": "ok",
            "tx_id": tx.id,
            "tx_status": tx.status,
            "steps_count": len(tx.steps)
        })
        return

    console.print(f"[green]{t('cli.sync.completed', count=len(plan.clients))}[/green]")
    console.print(f"[dim]Transaction ID: {tx.id} (Status: {tx.status})[/dim]")

@app.command("undo")
def undo_cmd(
    tx_id: Optional[str] = typer.Argument(None, help="Transaction ID to revert (defaults to last)"),
    as_json: bool = typer.Option(False, "--json", help="Output results in clean JSON format for scripts and agents")
):
    """Roll back configuration files using timestamped backups."""
    svc = USMService()
    success = svc.undo_transaction(tx_id)
    if as_json:
        console.print_json(data={"status": "ok" if success else "failed", "tx_id": tx_id or "latest"})
        return

    if success:
        console.print(f"[green]{t('cli.undo.success', tx_id=tx_id or 'latest')}[/green]")
    else:
        console.print("[red]Could not undo transaction (no backup or transaction not found).[/red]")

@app.command("mcp")
def mcp_cmd():
    """Run the Universal Skill Manager MCP Server over stdio for AI agent tool calling."""
    from usm.mcp.server import run_mcp_server
    run_mcp_server()

@app.command("setup-agent")
def setup_agent_cmd(
    client: Optional[str] = typer.Option(None, "--client", help="Specific client to install into (default: all installed clients)"),
    as_json: bool = typer.Option(False, "--json", help="Output results in clean JSON format for scripts and agents")
):
    """Automatically configure AI agent clients (Antigravity, Claude, Cursor) to use USM as an MCP tool and agent skill."""
    from usm.core.prompt_engine import PromptSkillDeployer
    svc = USMService()

    # 1. Register USM MCP Server
    python_exe = sys.executable
    mcp_skill = Skill(
        id="usm",
        name="Universal Skill Manager",
        description="Autonomous MCP & Skill Manager for AI agents",
        kind="mcp_server",
        transport=Transport.STDIO,
        command=python_exe,
        args=["-m", "usm", "mcp"],
        targets="all" if not client else [TargetBinding(client_id=client)]
    )
    tx = svc.add_skill(mcp_skill, auto_sync=True)

    # 2. Deploy Universal Skill Manager Agent Skill instruction
    agent_instructions = (
        "# Universal Skill Manager (USM) - Autonomous Agent Guidelines\n\n"
        "This skill enables AI agents to centrally manage and synchronize MCP servers and rule skills across this workstation.\n\n"
        "When the user asks you to install tools, add MCP servers, or configure agent rules/skills, use the USM MCP tools or the `usm` CLI commands.\n\n"
        "### Available USM MCP Tools\n"
        "- `usm_status`: Reports AI client detection and health status.\n"
        "- `usm_scan_clients`: Scans the host environment for installed AI tools, runtimes, and editors.\n"
        "- `usm_register_client`: Dynamically registers new custom AI clients and editors.\n"
        "- `usm_list_skills`: Lists all configured MCP servers and prompt skills.\n"
        "- `usm_add_mcp_server`: Installs and binds a new MCP tool across AI clients.\n"
        "- `usm_add_prompt_skill`: Creates and synchronizes a Markdown rule or prompt skill.\n"
        "- `usm_remove_skill`: Uninstalls a skill or MCP server.\n"
        "- `usm_sync_all`: Synchronizes configurations across all detected clients.\n"
        "- `usm_undo`: Reverts the last configuration change using timestamped backups.\n\n"
        "### Headless CLI Commands (JSON)\n"
        "- `usm status --json`\n"
        "- `usm scan --json`\n"
        "- `usm register-client <id> --config-path <path> --name <name> --json`\n"
        "- `usm list --json`\n"
        "- `usm add <id> --cmd <command> --args \"<arguments>\" --json`\n"
        "- `usm add <id> --kind prompt --content \"<markdown>\" --json`\n"
        "- `usm remove <id> --json`\n"
        "- `usm sync --json`\n"
        "- `usm undo --json`\n"
    )

    prompt_skill = Skill(
        id="universal-skill-manager",
        name="universal-skill-manager",
        description="Autonomous instructions for AI agents on using USM to manage tools and skills",
        kind="agent_skill",
        content=agent_instructions,
        scope="auto",
        targets="all" if not client else [TargetBinding(client_id=client)]
    )
    svc.add_skill(prompt_skill, auto_sync=True)

    if as_json:
        console.print_json(data={
            "status": "ok",
            "message": "Universal Skill Manager MCP tool and Agent Skill configured successfully.",
            "tx_id": tx.id if tx else None
        })
    else:
        console.print(Panel(
            "[green]✔ Universal Skill Manager successfully registered as an MCP tool and Agent Skill across AI clients![/green]\n"
            "Now any agent (Antigravity, Claude, Cursor, etc.) can manage tools and skills autonomously.",
            title="Agent Integration Complete",
            border_style="green"
        ))

@app.command("history")
def history_cmd():
    """Display audit history of past transactions."""
    svc = USMService()
    txs = svc.journal_mgr.list_transactions()
    if not txs:
        console.print("[dim]No transactions recorded yet.[/dim]")
        return

    table = Table(title="Transaction History", border_style="cyan")
    table.add_column("Tx ID", style="bold")
    table.add_column("Timestamp")
    table.add_column("Status")
    table.add_column("Steps")

    for tx in txs:
        status_style = "[green]" if tx.status == "applied" else "[yellow]"
        table.add_row(tx.id, tx.created_at.strftime("%Y-%m-%d %H:%M:%S"), f"{status_style}{tx.status}[/]", str(len(tx.steps)))

    console.print(table)

@app.command("export")
def export_cmd(
    target_path: Optional[Path] = typer.Argument(None, help="Output .usmpack archive file"),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output .usmpack archive file")
):
    """Export skills and settings to a portable .usmpack package."""
    svc = USMService()
    final_out = target_path or out or Path("my-skills.usmpack")
    p = svc.export_profile(final_out)
    console.print(f"[green]Profile exported to {p}[/green]")

@app.command("import")
def import_cmd(
    pkg: Path = typer.Argument(..., help="Path to .usmpack package to import"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing skill definitions")
):
    """Import skills from a portable .usmpack package."""
    svc = USMService()
    count = svc.import_profile(pkg, overwrite=overwrite)
    console.print(f"[green]Imported {count} skills from {pkg}[/green]")

@app.command("ui")
def ui_cmd(
    port: int = typer.Option(8765, "--port", help="Port for local Web UI"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open web browser automatically")
):
    """Launch the beautiful local Web UI dashboard."""
    import webbrowser
    import uvicorn
    from usm.web.server import create_app

    web_app = create_app()
    url = f"http://127.0.0.1:{port}"
    console.print(Panel(f"Universal Skill Manager Web UI is launching at [bold underline]{url}[/bold underline]\nPress Ctrl+C to stop.", title="Web UI", border_style="green"))

    if not no_browser:
        webbrowser.open(url)

    uvicorn.run(web_app, host="127.0.0.1", port=port, log_level="warning")

@app.command("scan")
def scan_cmd(
    auto_register: bool = typer.Option(False, "--auto-register", help="Automatically register detected unmanaged MCP-capable clients"),
    as_json: bool = typer.Option(False, "--json", help="Output results in JSON format for scripts and agents")
):
    """Scan host system for installed AI applications, runtimes, and editors."""
    svc = USMService()
    results = svc.scan_environment(auto_register=auto_register)

    if as_json:
        console.print_json(data=[r.model_dump() for r in results])
        return

    table = Table(title="AI Client & Ecosystem Discovery", border_style="cyan")
    table.add_column("ID", style="bold cyan")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Path / Details")
    table.add_column("Recommendation")

    for r in results:
        status_str = "[green]Installed[/green]" if r.installed else "[dim]Not found[/dim]"
        if r.running:
            status_str += " [bold yellow](Running)[/bold yellow]"
        
        type_str = "[green]Managed[/green]" if r.managed else "[cyan]External[/cyan]"
        path_str = r.path or "-"
        table.add_row(r.id, r.name, type_str, status_str, path_str, r.recommendation)

    console.print(table)
    if auto_register:
        console.print("[green]✔ Auto-registered any compatible discovered AI clients.[/green]")

@app.command("register-client")
def register_client_cmd(
    client_id: str = typer.Argument(..., help="Unique identifier for the client (e.g. continue, zed, my-ai)"),
    config_path: str = typer.Option(..., "--config-path", "-c", help="Path to the client configuration file"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Display name for the client"),
    root_key: str = typer.Option("mcpServers", "--root-key", "-r", help="JSON/TOML root key where MCP servers reside (e.g. mcpServers, context_servers)"),
    syntax: str = typer.Option("json", "--syntax", "-s", help="Syntax format: 'json' or 'toml'"),
    skills_dir: Optional[str] = typer.Option(None, "--skills-dir", help="Optional directory for prompt skills or rules"),
    as_json: bool = typer.Option(False, "--json", help="Output results in JSON format")
):
    """Register a new custom AI client dynamically without modifying code."""
    svc = USMService()
    display_name = name or client_id.title()
    success = svc.register_client(
        client_id=client_id,
        name=display_name,
        config_path=config_path,
        root_key=root_key,
        syntax=syntax,
        skills_dir=skills_dir
    )

    if as_json:
        console.print_json(data={
            "status": "success" if success else "failed",
            "client_id": client_id,
            "display_name": display_name,
            "config_path": config_path,
            "root_key": root_key,
            "syntax": syntax,
        })
        return

    console.print(f"[bold green]✔ Successfully registered AI client '{client_id}' ({display_name})![/bold green]")
    console.print(f"  [dim]Config Path: {config_path}[/dim]")
    console.print(f"  [dim]Root Key: {root_key}[/dim]")
    console.print(f"  [dim]Syntax: {syntax}[/dim]")
    console.print(f"You can now target this client using: [cyan]usm sync[/cyan] or [cyan]usm add <skill> --targets {client_id}[/cyan]")


def print_plan(plan):
    console.print(f"\n[bold]{t('cli.plan.title')} - {plan.id}[/bold]")
    for cp in plan.clients:
        active = [op for op in cp.ops if op.kind != OpKind.NOOP]
        if not active:
            console.print(f"  [dim]{cp.client_id}: No changes needed (in sync)[/dim]")
            continue
        console.print(f"  [cyan bold]{cp.client_id}[/cyan bold] ({cp.config_path}):")
        for op in active:
            if op.kind == OpKind.ADD:
                console.print(f"    [green]+ ADD[/green] {op.server_name} ({op.reason_key})")
            elif op.kind == OpKind.UPDATE:
                console.print(f"    [yellow]~ UPDATE[/yellow] {op.server_name}")
            elif op.kind == OpKind.REMOVE:
                console.print(f"    [red]- REMOVE[/red] {op.server_name}")
            elif op.kind == OpKind.ADOPT:
                console.print(f"    [blue]★ ADOPT[/blue] {op.server_name}")
            elif op.kind == OpKind.CONFLICT:
                console.print(f"    [red bold]! CONFLICT[/red bold] {op.server_name}")

if __name__ == "__main__":
    app()
