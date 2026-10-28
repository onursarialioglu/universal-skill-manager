import json
from pathlib import Path
from typer.testing import CliRunner
from usm.cli import app

runner = CliRunner()

def test_cli_status_json(temp_usm_home):
    res = runner.invoke(app, ["status", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert isinstance(data, list)
    assert len(data) >= 6
    assert any(c["client_id"] == "antigravity" for c in data)

def test_cli_list_json(temp_usm_home):
    res = runner.invoke(app, ["list", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert isinstance(data, list)

def test_cli_add_and_remove_json(tmp_path, monkeypatch, temp_usm_home):
    monkeypatch.chdir(tmp_path)
    
    # Add MCP server via JSON
    res = runner.invoke(app, [
        "add", "test-tool",
        "--cmd", "npx",
        "--args", "-y @modelcontextprotocol/server-github",
        "--json"
    ])
    assert res.exit_code == 0
    add_data = json.loads(res.output)
    assert add_data["status"] == "ok"
    assert add_data["skill_id"] == "test-tool"

    # List via JSON
    res = runner.invoke(app, ["list", "--json"])
    assert res.exit_code == 0
    list_data = json.loads(res.output)
    assert any(s["id"] == "test-tool" for s in list_data)

    # Remove via JSON
    res = runner.invoke(app, ["remove", "test-tool", "--json"])
    assert res.exit_code == 0
    rem_data = json.loads(res.output)
    assert rem_data["status"] == "ok"

def test_cli_setup_agent(tmp_path, monkeypatch, temp_usm_home):
    monkeypatch.chdir(tmp_path)
    
    res = runner.invoke(app, ["setup-agent", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["status"] == "ok"

    # Verify agent skill file was written
    ag_skill = tmp_path / ".agents" / "skills" / "universal-skill-manager" / "SKILL.md"
    assert ag_skill.exists()
    content = ag_skill.read_text(encoding="utf-8")
    assert "Universal Skill Manager" in content
    assert "usm_add_mcp_server" in content

    # Verify both MCP server and Prompt Skill exist in registry
    from usm.core.service import USMService
    svc = USMService()
    reg = svc.registry_mgr.load()
    assert "usm" in reg.skills
    assert reg.skills["usm"].kind == "mcp_server"
    assert "universal-skill-manager" in reg.skills
    assert reg.skills["universal-skill-manager"].kind == "agent_skill"
