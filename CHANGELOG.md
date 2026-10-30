# Changelog

All notable changes to **Universal Skill Manager (USM)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-10-30

### Added
- **AI Ecosystem Discovery Scanner**: Integrated `AIScanner` engine (`usm scan`) detecting installed AI clients, runtimes (Ollama, LM Studio, Gemini Desktop), Qwen Code CLI (`~/.qwen/settings.json`), and DeepSeek Harness (`~/.dsh`).
- **Dynamic Client Registration**: Implemented `DynamicClientAdapter` allowing users and agents to connect any custom or newly released AI client (`usm register-client`) via JSON/TOML configuration without modifying source code.
- **Agent Scanner Tools**: Expanded USM MCP server from 7 to 9 tools (`usm_scan_clients`, `usm_register_client`) enabling autonomous discovery and client onboarding by AI agents.
- **42 Comprehensive Automated Tests**: Added unit and end-to-end test suites for the scanner, dynamic client registration, and ecosystem adapters.
- **Enhanced Documentation & Onboarding**: Streamlined cross-platform setup, updated repository URLs, and foolproof PowerShell / POSIX virtual environment instructions.

## [0.1.0] - 2026-10-25

### Added
- **Unified Architecture**: Cross-platform configuration orchestrator for Antigravity, Claude Desktop, Claude Code, VS Code, Cursor, Windsurf, Roo Code, and Cline.
- **3-Way Merging Engine**: Intelligent merge engine preserving user-configured unmanaged MCP servers without accidental overwrites.
- **Atomic File I/O & Rollbacks**: Automated timestamped backups before writes, file-locking, post-write validation, and instant `usm undo` rollback capability.
- **USM MCP v2 Server**: Built-in standard Model Context Protocol server (`usm mcp`) exposing 7 core tools for AI agents (`usm_status`, `usm_list_skills`, `usm_add_mcp_server`, `usm_add_prompt_skill`, `usm_remove_skill`, `usm_sync_all`, `usm_undo`).
- **Autonomous Agent Integration**: `usm setup-agent` command configuring USM across all installed AI clients and distributing universal agent guidelines (`SKILL.md`).
- **Prompt & Rule Skills**: Deploy and synchronize Markdown instructions and prompt rules across `.agents/skills`, `.claude/skills`, `.cursor/rules`, `.windsurf/rules`, and `.clinerules`.
- **Modern Local Web UI**: Sleek dark-mode dashboard (`usm ui`) powered by FastAPI and Vanilla CSS/JS.
- **Headless CLI**: Full `--json` flag support across `status`, `list`, `add`, `remove`, `sync`, and `undo` commands for scripting and terminal agents.
- **Extensible Architecture**: Clean modular codebase prepared for community adapters and extensions.
- **Portability Packages**: Export and import complete skill configurations with `.usmpack` archives.
