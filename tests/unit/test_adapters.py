from usm.adapters import get_all_adapters, get_adapter
from usm.models import Skill, Transport

def test_all_adapters_load():
    adapters = get_all_adapters()
    assert len(adapters) >= 7
    ids = [a.id for a in adapters]
    assert "claude-desktop" in ids
    assert "antigravity" in ids
    assert "roo-code" in ids
    assert "cline" in ids
    assert "vscode" in ids
    assert "cursor" in ids
    assert "windsurf" in ids

def test_claude_adapter_to_native():
    adapter = get_adapter("claude-desktop")
    assert adapter is not None

    skill = Skill(
        id="test-srv",
        name="Test",
        transport=Transport.STDIO,
        command="npx",
        args=["-y", "test-server"],
        env={"API_KEY": "12345"}
    )

    native = adapter.to_native(skill)
    assert native["command"] == "npx"
    assert native["args"] == ["-y", "test-server"]
    assert native["env"] == {"API_KEY": "12345"}

def test_antigravity_adapter_to_native():
    adapter = get_adapter("antigravity")
    assert adapter is not None

    skill = Skill(
        id="remote-srv",
        name="Remote",
        transport=Transport.HTTP,
        url="https://api.example.com/mcp"
    )

    native = adapter.to_native(skill)
    assert native["serverUrl"] == "https://api.example.com/mcp"

def test_codex_adapter(tmp_path):
    adapter = get_adapter("codex")
    assert adapter is not None
    assert adapter.id == "codex"

    # Test alias
    chatgpt_adapter = get_adapter("chatgpt")
    assert chatgpt_adapter is not None
    assert chatgpt_adapter.id == "codex"

    # Test TOML read and write
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('model = "gpt-5"\n\n[mcp_servers.old]\ncommand = "node"\nargs = ["server.js"]\n', encoding="utf-8")

    data, fmt = adapter.read_config(cfg_file)
    assert fmt == "toml"
    assert data["model"] == "gpt-5"
    assert "old" in data["mcp_servers"]

    # Add new server
    data["mcp_servers"]["new-server"] = {"command": "python", "args": ["-m", "new_srv"]}
    adapter.write_config(cfg_file, data)

    updated_data, _ = adapter.read_config(cfg_file)
    assert "old" in updated_data["mcp_servers"]
    assert "new-server" in updated_data["mcp_servers"]
    assert updated_data["model"] == "gpt-5"
