import pytest
from pathlib import Path
from usm.core.scanner import AIScanner, DiscoveredApp
from usm.settings import Settings

def test_ai_scanner_scan(temp_usm_home, monkeypatch, tmp_path):
    settings = Settings()
    results = AIScanner.scan(settings)
    assert isinstance(results, list)
    assert len(results) > 0
    
    # Check that each result conforms to DiscoveredApp
    for app in results:
        assert isinstance(app, DiscoveredApp)
        assert app.id
        assert app.name
        assert app.category in ("managed_client", "mcp_client", "ai_runtime", "consumer_shell")
        assert isinstance(app.installed, bool)
        assert isinstance(app.running, bool)
        assert isinstance(app.recommendation, str)

def test_ai_scanner_mock_detection(temp_usm_home, monkeypatch, tmp_path):
    # Simulate a Continue.dev config file
    continue_cfg = tmp_path / "continue_config.json"
    continue_cfg.write_text('{"mcpServers": {}}', encoding="utf-8")

    mock_apps = [
        {
            "id": "mock-continue",
            "name": "Mock Continue",
            "category": "mcp_client",
            "mcp_capable": True,
            "detect_paths": [str(continue_cfg)],
            "process_names": [],
            "syntax": "json",
            "root_key": "mcpServers",
            "recommendation": "Mock detected",
        }
    ]
    monkeypatch.setattr(AIScanner, "KNOWN_EXTERNAL_APPS", mock_apps)

    settings = Settings()
    results = AIScanner.scan(settings)
    
    matched = [r for r in results if r.id == "mock-continue"]
    assert len(matched) == 1
    assert matched[0].installed is True
    assert matched[0].path == str(continue_cfg)
    assert matched[0].mcp_capable is True

def test_ai_scanner_auto_register(temp_usm_home, monkeypatch, tmp_path):
    continue_cfg = tmp_path / "continue_config.json"
    continue_cfg.write_text('{"mcpServers": {}}', encoding="utf-8")

    mock_apps = [
        {
            "id": "auto-test-ai",
            "name": "Auto Test AI",
            "category": "mcp_client",
            "mcp_capable": True,
            "detect_paths": [str(continue_cfg)],
            "process_names": [],
            "syntax": "json",
            "root_key": "mcpServers",
            "recommendation": "Ready to auto-register",
        }
    ]
    monkeypatch.setattr(AIScanner, "KNOWN_EXTERNAL_APPS", mock_apps)

    settings = Settings()
    registered = AIScanner.auto_register_detected(settings)
    assert "auto-test-ai" in registered
    assert "auto-test-ai" in settings.clients
    assert settings.clients["auto-test-ai"].custom is True
    assert settings.clients["auto-test-ai"].path_override == str(continue_cfg)

def test_ai_scanner_detects_deepseek_harness(temp_usm_home, monkeypatch, tmp_path):
    dsh_dir = tmp_path / ".dsh"
    dsh_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    settings = Settings()
    results = AIScanner.scan(settings)

    matched = [r for r in results if r.id == "deepseek-harness"]
    assert len(matched) == 1
    assert matched[0].installed is True
    assert matched[0].mcp_capable is True
    assert "deepseek" in matched[0].id.lower()

def test_ai_scanner_detects_qwen_code(temp_usm_home, monkeypatch, tmp_path):
    qwen_cfg = tmp_path / ".qwen" / "settings.json"
    qwen_cfg.parent.mkdir(parents=True, exist_ok=True)
    qwen_cfg.write_text('{"mcpServers": {}}', encoding="utf-8")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    settings = Settings()
    results = AIScanner.scan(settings)

    matched = [r for r in results if r.id == "qwen-code"]
    assert len(matched) == 1
    assert matched[0].installed is True
    assert matched[0].mcp_capable is True
    assert "qwen" in matched[0].id.lower()


