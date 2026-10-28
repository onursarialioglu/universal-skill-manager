from fastapi.testclient import TestClient
from usm.web.server import create_app

def test_web_api(temp_usm_home):
    app = create_app()
    client = TestClient(app)

    # Status
    res = client.get("/api/status")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Skills initially empty
    res = client.get("/api/skills")
    assert res.status_code == 200
    assert len(res.json()) == 0

    # Add skill
    res = client.post("/api/skills", json={
        "id": "my-tool",
        "name": "My Tool",
        "command": "python",
        "args": ["run.py"]
    })
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # Verify skill appears
    res = client.get("/api/skills")
    assert len(res.json()) == 1
    assert res.json()[0]["id"] == "my-tool"

    # Delete skill
    res = client.delete("/api/skills/my-tool")
    assert res.status_code == 200

    res = client.get("/api/skills")
    assert len(res.json()) == 0

def test_web_add_prompt_skill(tmp_path, monkeypatch, temp_usm_home):
    monkeypatch.chdir(tmp_path)
    app = create_app()
    client = TestClient(app)

    res = client.post("/api/skills", json={
        "id": "api-design-standard",
        "name": "API Design Standard",
        "description": "Standard REST API design guidelines",
        "kind": "agent_skill",
        "content": "# API Design Guidelines\nUse semantic versioning and clear payloads.",
        "targets": []
    })
    assert res.status_code == 200
    assert res.json()["kind"] == "agent_skill"

    # Verify skill appears with kind
    res = client.get("/api/skills")
    assert res.status_code == 200
    skills = res.json()
    assert len(skills) == 1
    assert skills[0]["kind"] == "agent_skill"
    assert skills[0]["content"] == "# API Design Guidelines\nUse semantic versioning and clear payloads."

    # Verify deployed file
    ag_file = tmp_path / ".agents" / "skills" / "api-design-standard" / "SKILL.md"
    assert ag_file.exists()
    assert "name: api-design-standard" in ag_file.read_text(encoding="utf-8")

def test_settings_api(temp_usm_home):
    app = create_app()
    client = TestClient(app)

    # GET Settings
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "language" in data
    assert "approval_mode" in data
    assert "backup" in data

    # PUT Settings
    res = client.put("/api/settings", json={
        "language": "en",
        "approval_mode": "auto",
        "backup": {
            "per_client_retention": 35,
            "retention_days": 45,
            "mirror_central": True
        }
    })
    assert res.status_code == 200
    updated = res.json()["settings"]
    assert updated["language"] == "en"
    assert updated["approval_mode"] == "auto"
    assert updated["backup"]["per_client_retention"] == 35

def test_templates_api(temp_usm_home):
    app = create_app()
    client = TestClient(app)

    res = client.get("/api/templates")
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) > 0
