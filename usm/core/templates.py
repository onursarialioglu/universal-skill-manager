from pathlib import Path
from typing import Dict, List
from usm.models import PlatformOverride, Runner, Skill, Transport

_BUILTIN_TEMPLATES: Dict[str, Skill] = {
    "github": Skill(
        id="github",
        name="GitHub",
        description="GitHub repositories, issues, PRs, and code exploration",
        transport=Transport.STDIO,
        runner=Runner.NPX,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_GITHUB_TOKEN"},
        platforms={
            "windows": PlatformOverride(command="cmd", args=["/c", "npx", "-y", "@modelcontextprotocol/server-github"])
        },
        tags=["dev", "git"]
    ),
    "filesystem": Skill(
        id="filesystem",
        name="Filesystem",
        description="Secure local file access for specific allowed directories",
        transport=Transport.STDIO,
        runner=Runner.NPX,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", str(Path.home())],
        platforms={
            "windows": PlatformOverride(command="cmd", args=["/c", "npx", "-y", "@modelcontextprotocol/server-filesystem", str(Path.home())])
        },
        tags=["files", "tools"]
    ),
    "fetch": Skill(
        id="fetch",
        name="Fetch",
        description="Web content fetching and conversion to markdown for LLMs",
        transport=Transport.STDIO,
        runner=Runner.UVX,
        command="uvx",
        args=["mcp-server-fetch"],
        platforms={
            "windows": PlatformOverride(command="cmd", args=["/c", "uvx", "mcp-server-fetch"])
        },
        tags=["web", "tools"]
    ),
    "sqlite": Skill(
        id="sqlite",
        name="SQLite",
        description="Query and inspect local SQLite databases",
        transport=Transport.STDIO,
        runner=Runner.UVX,
        command="uvx",
        args=["mcp-server-sqlite", "--db-path", "test.db"],
        platforms={
            "windows": PlatformOverride(command="cmd", args=["/c", "uvx", "mcp-server-sqlite", "--db-path", "test.db"])
        },
        tags=["database"]
    ),
    "memory": Skill(
        id="memory",
        name="Memory",
        description="Knowledge graph-based persistent memory server",
        transport=Transport.STDIO,
        runner=Runner.NPX,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-memory"],
        platforms={
            "windows": PlatformOverride(command="cmd", args=["/c", "npx", "-y", "@modelcontextprotocol/server-memory"])
        },
        tags=["knowledge"]
    )
}

def get_template(template_id: str) -> Skill:
    if template_id in _BUILTIN_TEMPLATES:
        return _BUILTIN_TEMPLATES[template_id].model_copy(deep=True)
    raise KeyError(f"Template '{template_id}' not found.")

def list_templates() -> List[Skill]:
    return list(_BUILTIN_TEMPLATES.values())
