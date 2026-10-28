import os
import shutil
import tempfile
from pathlib import Path
import pytest

@pytest.fixture
def temp_usm_home(monkeypatch):
    temp_dir = Path(tempfile.mkdtemp(prefix="usm_test_"))
    monkeypatch.setenv("USM_HOME", str(temp_dir))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def mock_client_configs(tmp_path):
    # Create realistic mock configs for Claude, Antigravity, Roo Code
    claude_cfg = tmp_path / "claude_desktop_config.json"
    claude_cfg.write_text('{"mcpServers": {"existing_custom": {"command": "npx", "args": ["custom-pkg"]}}}', encoding="utf-8")

    antigravity_cfg = tmp_path / "antigravity_config.json"
    antigravity_cfg.write_text('{"mcpServers": {}}', encoding="utf-8")

    roo_cfg = tmp_path / "roo_settings.json"
    roo_cfg.write_text('{"mcpServers": {"my_tool": {"command": "python", "args": ["tool.py"], "disabled": false}}}', encoding="utf-8")

    return {
        "claude": claude_cfg,
        "antigravity": antigravity_cfg,
        "roo": roo_cfg
    }
