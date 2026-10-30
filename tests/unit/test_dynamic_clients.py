import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from usm.adapters import get_adapter, get_all_adapters
from usm.adapters.dynamic import DynamicClientAdapter
from usm.cli import app
from usm.core.service import USMService
from usm.mcp.server import create_mcp_server
from usm.models import Skill, Transport
from usm.settings import ClientSetting

runner = CliRunner()

def test_dynamic_client_adapter_flow(tmp_path):
    config_file = tmp_path / "custom_app_config.json"
    config_file.write_text('{"mcpServers": {"pre_existing": {"command": "node"}}}', encoding="utf-8")

    setting = ClientSetting(
        enabled=True,
        path_override=str(config_file),
        display_name="Custom AI Studio",
        syntax="json",
        root_key="mcpServers",
        custom=True
    )
    adapter = DynamicClientAdapter("custom-ai", setting)
    assert adapter.id == "custom-ai"
    assert adapter.display_name_key == "Custom AI Studio"

    # Test status
    from usm.settings import Settings
    settings = Settings()
    settings.clients["custom-ai"] = setting
    status = adapter.get_status(settings)
    assert status.status.value == "ready"
    assert status.path == config_file

    # Test read / write
    raw, fmt = adapter.read_config(config_file)
    assert "pre_existing" in adapter.read_servers(raw)

    # To native
    sk = Skill(id="git-tool", name="Git Tool", transport=Transport.STDIO, command="uvx", args=["mcp-server-git"])
    native = adapter.to_native(sk)
    assert native["command"] == "uvx"
    assert native["args"] == ["mcp-server-git"]

def test_service_register_and_sync_dynamic_client(temp_usm_home, tmp_path):
    svc = USMService()
    config_file = tmp_path / "custom_tool.json"
    config_file.write_text('{"mcpServers": {}}', encoding="utf-8")

    # 1. Register client
    svc.register_client(
        client_id="my-custom-ai",
        name="My Custom AI",
        config_path=str(config_file),
        root_key="mcpServers",
        syntax="json"
    )

    # 2. Adapter should be loaded in get_all_adapters()
    adapters = get_all_adapters()
    adp_ids = [a.id for a in adapters]
    assert "my-custom-ai" in adp_ids

    adapter = get_adapter("my-custom-ai")
    assert adapter is not None
    assert adapter.id == "my-custom-ai"

    # 3. Add skill targeting my-custom-ai
    skill = Skill(
        id="sqlite-server",
        name="SQLite Server",
        transport=Transport.STDIO,
        command="uvx",
        args=["mcp-server-sqlite"],
        targets="all"
    )
    svc.add_skill(skill, auto_sync=True)

    # 4. Check config file was updated by 3-way merge
    content = json.loads(config_file.read_text(encoding="utf-8"))
    assert "sqlite-server" in content["mcpServers"]
    assert content["mcpServers"]["sqlite-server"]["command"] == "uvx"

def test_cli_scan_and_register_client(temp_usm_home, tmp_path):
    # 1. CLI scan
    res = runner.invoke(app, ["scan"])
    assert res.exit_code == 0
    assert "AI Client & Ecosystem Discovery" in res.output

    # 2. CLI scan --json
    res = runner.invoke(app, ["scan", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert isinstance(data, list)

    # 3. CLI register-client
    cfg = tmp_path / "cli_client.json"
    cfg.write_text("{}", encoding="utf-8")
    res = runner.invoke(app, [
        "register-client", "cli-test-ai",
        "--config-path", str(cfg),
        "--name", "CLI Test AI",
        "--root-key", "mcpServers",
        "--json"
    ])
    assert res.exit_code == 0
    resp_data = json.loads(res.output)
    assert resp_data["status"] == "success"
    assert resp_data["client_id"] == "cli-test-ai"

@pytest.mark.anyio
async def test_mcp_server_scan_and_register(temp_usm_home, tmp_path):
    server = create_mcp_server()
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    assert "usm_scan_clients" in tool_names
    assert "usm_register_client" in tool_names

    # Test call usm_scan_clients
    res = await server.call_tool("usm_scan_clients", {})
    assert "discovered_apps" in res.content[0].text

    # Test call usm_register_client
    cfg = tmp_path / "mcp_ai_test.json"
    cfg.write_text("{}", encoding="utf-8")
    reg_res = await server.call_tool("usm_register_client", {
        "client_id": "agent-discovered-ai",
        "name": "Agent Discovered AI",
        "config_path": str(cfg),
        "root_key": "mcpServers"
    })
    assert "success" in reg_res.content[0].text
