import pytest
import asyncio
from usm.mcp.server import create_mcp_server

@pytest.mark.anyio
async def test_mcp_server_tools_list():
    server = create_mcp_server()
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    
    assert "usm_status" in tool_names
    assert "usm_list_skills" in tool_names
    assert "usm_add_mcp_server" in tool_names
    assert "usm_add_prompt_skill" in tool_names
    assert "usm_remove_skill" in tool_names
    assert "usm_sync_all" in tool_names
    assert "usm_undo" in tool_names
    assert len(tool_names) == 7

@pytest.mark.anyio
async def test_mcp_server_add_and_list_mcp(temp_usm_home):
    server = create_mcp_server()
    
    # 1. Add MCP server
    res = await server.call_tool("usm_add_mcp_server", {
        "id": "agent-fetch",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "description": "Web scraper tool"
    })
    assert not res.is_error
    assert "success" in str(res.content)

    # 2. List skills
    list_res = await server.call_tool("usm_list_skills", {"kind": "mcp_server"})
    assert not list_res.is_error
    assert "agent-fetch" in str(list_res.content)

    # 3. Remove skill
    rem_res = await server.call_tool("usm_remove_skill", {"id": "agent-fetch"})
    assert not rem_res.is_error
    assert "removed" in str(rem_res.content).lower()

@pytest.mark.anyio
async def test_mcp_server_add_prompt_skill(tmp_path, monkeypatch, temp_usm_home):
    monkeypatch.chdir(tmp_path)
    server = create_mcp_server()

    # 1. Add prompt skill
    res = await server.call_tool("usm_add_prompt_skill", {
        "id": "python-standards-rule",
        "name": "Python Standards Rule",
        "content": "# Python Coding Standards\nFollow PEP8 and use type hints.",
        "description": "Standard Python engineering guidelines"
    })
    assert not res.is_error
    assert "success" in str(res.content)

    # Check file deployed
    skill_file = tmp_path / ".agents" / "skills" / "python-standards-rule" / "SKILL.md"
    assert skill_file.exists()
    assert "name: python-standards-rule" in skill_file.read_text(encoding="utf-8")

    # 2. Remove
    rem_res = await server.call_tool("usm_remove_skill", {"id": "python-standards-rule"})
    assert not rem_res.is_error
    assert not skill_file.exists()
