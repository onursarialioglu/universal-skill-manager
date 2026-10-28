---
name: universal-skill-manager
description: "Autonomous instructions for AI agents on using USM to manage tools and skills"
---

# Universal Skill Manager (USM) - Autonomous Agent Guidelines

This skill enables AI agents to centrally manage and synchronize MCP servers and rule skills across this workstation.

When the user asks you to install tools, add MCP servers, or configure agent rules/skills, use the USM MCP tools or the `usm` CLI commands.

### Available USM MCP Tools
- `usm_status`: Reports AI client detection and health status.
- `usm_list_skills`: Lists all configured MCP servers and prompt skills.
- `usm_add_mcp_server`: Installs and binds a new MCP tool across AI clients.
- `usm_add_prompt_skill`: Creates and synchronizes a Markdown rule or prompt skill.
- `usm_remove_skill`: Uninstalls a skill or MCP server.
- `usm_sync_all`: Synchronizes configurations across all detected clients.
- `usm_undo`: Reverts the last configuration change using timestamped backups.

### Headless CLI Commands (JSON)
- `usm status --json`
- `usm list --json`
- `usm add <id> --cmd <command> --args "<arguments>" --json`
- `usm add <id> --kind prompt --content "<markdown>" --json`
- `usm remove <id> --json`
- `usm sync --json`
- `usm undo --json`
