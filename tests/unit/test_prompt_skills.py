import pytest
from pathlib import Path
from usm.models import Skill, TargetBinding
from usm.core.prompt_engine import PromptSkillDeployer
from usm.core.service import USMService

def test_prompt_deployer_format():
    formatted = PromptSkillDeployer.format_frontmatter(
        skill_id="code-style-test",
        description="Clean code style guidelines",
        content="# Test Content\nRule 1"
    )
    assert "name: code-style-test" in formatted
    assert "description: \"Clean code style guidelines\"" in formatted
    assert "# Test Content" in formatted

def test_prompt_deployer_deploy_and_remove(tmp_path, temp_usm_home):
    skill = Skill(
        id="api-standards",
        name="REST API Standards",
        description="RESTful API design and status codes",
        kind="agent_skill",
        content="# API Design Standards\n\nAlways use proper HTTP status codes and JSON envelopes.",
        targets=[TargetBinding(client_id="antigravity"), TargetBinding(client_id="cursor")]
    )

    # Deploy to tmp workspace
    results = PromptSkillDeployer.deploy_skill(skill, base_dir=tmp_path)
    assert "antigravity" in results
    assert "cursor" in results

    ag_file = tmp_path / ".agents" / "skills" / "api-standards" / "SKILL.md"
    cursor_file = tmp_path / ".cursor" / "rules" / "api-standards.mdc"

    assert ag_file.exists()
    assert cursor_file.exists()

    content = ag_file.read_text(encoding="utf-8")
    assert "name: api-standards" in content
    assert "API Design Standards" in content

    # Remove
    removed = PromptSkillDeployer.remove_skill("api-standards", base_dir=tmp_path)
    assert not ag_file.exists()
    assert not cursor_file.exists()

def test_service_prompt_skill_flow(tmp_path, monkeypatch, temp_usm_home):
    monkeypatch.chdir(tmp_path)
    svc = USMService()

    skill = Skill(
        id="code-review-skill",
        name="Code Reviewer",
        description="Senior engineer review guidelines",
        kind="agent_skill",
        content="# Guidelines\nCheck edge cases, memory leaks, and tests.",
        targets="all"
    )

    svc.add_skill(skill, auto_sync=False)
    assert svc.get_skill("code-review-skill") is not None

    # Check that it deployed to workspace .agents/skills
    ag_file = tmp_path / ".agents" / "skills" / "code-review-skill" / "SKILL.md"
    assert ag_file.exists()

    # Remove
    svc.remove_skill("code-review-skill", auto_sync=False)
    assert svc.get_skill("code-review-skill") is None
    assert not ag_file.exists()

def test_prompt_deployer_codex_targets(tmp_path, temp_usm_home, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skill = Skill(
        id="git-workflow-rule",
        name="Git Workflow Standards",
        description="Conventional commits and pull request hygiene",
        kind="agent_skill",
        content="# Git Workflow\nUse semantic commit prefixes.",
        targets="all"
    )

    results = PromptSkillDeployer.deploy_skill(skill, base_dir=tmp_path)
    assert "codex" in results
    assert "antigravity" in results
    assert "claude_code" in results

    # Verify that codex path was generated
    codex_paths = PromptSkillDeployer.get_target_paths("git-workflow-rule", "codex", scope="auto", base_dir=tmp_path)
    assert any("skills" in str(p) and "git-workflow-rule" in str(p) for p in codex_paths)
