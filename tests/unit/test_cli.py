from typer.testing import CliRunner
from usm.cli import app

runner = CliRunner()

def test_cli_help():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "Universal Skill Manager" in res.output or "Usage:" in res.output

def test_cli_init(temp_usm_home):
    res = runner.invoke(app, ["init"])
    assert res.exit_code == 0
    assert "Universal Skill Manager" in res.output

def test_cli_add_list_remove(temp_usm_home):
    # 1. Add skill
    res = runner.invoke(app, ["add", "github", "--cmd", "npx", "--args", "-y @modelcontextprotocol/server-github", "--env", "GITHUB_TOKEN=abc"])
    assert res.exit_code == 0
    assert "github" in res.output.lower()

    # 2. List skills
    res = runner.invoke(app, ["list"])
    assert res.exit_code == 0
    assert "github" in res.output.lower()

    # 3. Remove skill
    res = runner.invoke(app, ["remove", "github"])
    assert res.exit_code == 0
    assert "github" in res.output.lower()

    # 4. List should now be empty
    res = runner.invoke(app, ["list"])
    assert res.exit_code == 0

def test_cli_add_prompt_skill(tmp_path, monkeypatch, temp_usm_home):
    monkeypatch.chdir(tmp_path)
    # Add prompt skill
    res = runner.invoke(app, [
        "add", "code-rule",
        "--kind", "prompt",
        "--desc", "Strict code review guidelines",
        "--content", "# Code Review Rules\nCheck for leaks and tests."
    ])
    assert res.exit_code == 0

    # List should show code-rule and Prompt
    res = runner.invoke(app, ["list"])
    assert res.exit_code == 0
    assert "code-rule" in res.output
    assert "Prompt" in res.output

    # Verify deployed file
    ag_file = tmp_path / ".agents" / "skills" / "code-rule" / "SKILL.md"
    assert ag_file.exists()
    assert "name: code-rule" in ag_file.read_text(encoding="utf-8")

    # Remove
    res = runner.invoke(app, ["remove", "code-rule"])
    assert res.exit_code == 0
    assert not ag_file.exists()
