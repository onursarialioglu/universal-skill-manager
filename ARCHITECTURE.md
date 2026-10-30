# Universal Skill Manager (USM) — Architecture Specification

> **Version:** 1.0 · **Status:** Production Architecture Specification · **License:** MIT  
> **Language:** English

---

## Table of Contents

1. [Executive Summary & Purpose](#1-executive-summary--purpose)
2. [Core Invariants & Design Principles](#2-core-invariants--design-principles)
3. [User Personas & Use Cases](#3-user-personas--use-cases)
4. [System Architecture](#4-system-architecture)
5. [Directory Layout](#5-directory-layout)
6. [Data Models & Schema](#6-data-models--schema)
7. [Central State & Registry (`~/.skill-manager`)](#7-central-state--registry)
8. [Client Adapters & Compatibility Layer](#8-client-adapters--compatibility-layer)
9. [Synchronization Engine (Plan → Verify → Apply → Audit)](#9-synchronization-engine)
10. [Safety Invariants & Non-Destructive Merging](#10-safety-invariants--non-destructive-merging)
11. [User Interfaces (CLI, Web UI, MCP Server)](#11-user-interfaces)
12. [Autonomous Agent Enablement](#12-autonomous-agent-enablement)
13. [Portability & Profiles (`.usmpack`)](#13-portability--profiles)
14. [Security, Sandboxing & Secrets Handling](#14-security-sandboxing--secrets-handling)
15. [Health Checking & Self-Healing](#15-health-checking--self-healing)
16. [Daemon & Drift Detection](#16-daemon--drift-detection)
17. [Diagnostics & Error Hierarchy](#17-diagnostics--error-hierarchy)
18. [Testing & Verification Strategy](#18-testing--verification-strategy)
19. [Roadmap](#19-roadmap)

---

## 1. Executive Summary & Purpose

### 1.1 The Multi-Agent Configuration Fragmentation Problem
Modern AI-assisted software development uses multiple specialized AI agents and environments concurrently on the same workstation:
- **OpenAI Codex CLI & VS Code Codex/ChatGPT**
- **Google Antigravity IDE**
- **Anthropic Claude Desktop & Claude Code CLI**
- **Cursor IDE**
- **Windsurf IDE (Codeium)**
- **VS Code Extension Ecosystems (Cline, Roo Code)**

Each environment maintains its own proprietary configuration format (JSON, JSONC, TOML), distinct configuration file paths (`~/.codex/config.toml`, `~/.claude/claude_desktop_config.json`, `.cursor/rules/`, `.agents/skills/`, etc.), and varying schemas for tools and instruction rules.

Manually registering a Model Context Protocol (MCP) server or instruction skill across 6+ clients is error-prone, inconsistent, fragile, and difficult to audit or rollback.

### 1.2 The Universal Skill Manager Solution
**Universal Skill Manager (USM)** serves as a single source of truth and cross-client synchronization hub for:
1. **MCP Servers (Executable Tools):** Command-line runners, stdio, SSE, and HTTP endpoints.
2. **Agent Skills (Instruction & Prompt Rules):** Markdown system instructions, domain rules, and workflow playbooks.

USM guarantees:
- **Central Management:** Add, edit, or remove tools in one place.
- **Zero-Loss 3-Way Merge:** Preserves unmanaged local configurations and custom settings.
- **Atomic File Operations:** Automated backups, atomic renames, and instant rollback.
- **Bi-Directional Access:** Accessible via CLI, interactive Web Dashboard, and native MCP tools for autonomous AI pair programming.

---

## 2. Core Invariants & Design Principles

```
┌─────────────────────────────────────────────────────────────┐
│                    USM Core Invariants                      │
├─────────────────────────────────────────────────────────────┤
│ 1. Non-Destructive 3-Way Merge (Never lose user tools)     │
│ 2. Pre-Write Backup & Atomic File Writes                   │
│ 3. Post-Write Bit-For-Bit Verification                      │
│ 4. Single-Action Transaction Rollback (Undo)                │
│ 5. Full Transparency: Dry-Run Diff Before Modification      │
│ 6. Cross-Platform Parity (Windows, macOS, Linux)           │
└─────────────────────────────────────────────────────────────┘
```

1. **Safety First (Non-Destructive):** A configuration write must never destroy or corrupt unmanaged client settings. Unmanaged servers configured by the user directly in Claude, Cursor, or Codex are safely retained.
2. **Explicit Verification:** Every file write is validated post-execution. If parse validation or content integrity fails, the transaction is immediately rolled back to its pre-operation snapshot.
3. **Dry-Run Transparency:** Every mutation generates a deterministic execution plan (`Plan`) highlighting diffs before application.
4. **Portability:** Configurations, settings, and skills can be bundled into encrypted or plain `.usmpack` archives for cross-machine migration.
5. **Headless & Autonomous:** Fully operable by human engineers via CLI/Web UI and by autonomous AI agents via the built-in MCP server.

---

## 3. User Personas & Use Cases

### 3.1 Software Engineer (Power User)
- Uses CLI (`usm add github --template github`, `usm list`, `usm sync`).
- Automates tool setups across dotfiles and new development machines.

### 3.2 Visual Practitioner & Team Lead
- Uses the local Web Dashboard (`usm ui`) to monitor client status, inspect tool health, and toggle active agents.

### 3.3 Autonomous AI Agent (Pair Programmer)
- Uses native MCP tools (`usm_add_mcp_server`, `usm_add_prompt_skill`, `usm_sync_all`) to configure environment tools autonomously upon user request.

---

## 4. System Architecture

```
                          ┌───────────────────────────┐
                          │   Human / Agent Clients   │
                          ├───────────┬───────────────┤
                          │  CLI      │  Web UI       │  MCP Protocol
                          │  (Typer)  │  (FastAPI)    │  (stdio)
                          └─────┬─────┴───────┬───────┴──────┬────────┘
                                │             │              │
                                ▼             ▼              ▼
                     ┌──────────────────────────────────────────────────┐
                     │             USM Core Service (Facade)            │
                     ├──────────────────────────────────────────────────┤
                     │  • Registry Manager     • Settings Manager       │
                     │  • Planner (Diff Engine)• Execution Engine       │
                     │  • Backup Manager       • Journal & Audit Log    │
                     │  • Health Checker       • Prompt Deployer        │
                     └────────────────────────┬─────────────────────────┘
                                              │
                      ┌───────────────────────┴────────────────────────┐
                      ▼                                                ▼
         ┌─────────────────────────┐                      ┌─────────────────────────┐
         │ Profile-Driven Adapters │                      │  Prompt Skill Deployer  │
         ├─────────────────────────┤                      ├─────────────────────────┤
         │ • Codex (TOML)          │                      │ • Global (.codex/skills)│
         │ • Antigravity (JSON)    │                      │ • Global (.claude/skills│
         │ • Claude Code / Desktop │                      │ • Global (.gemini/config│
         │ • Cursor / Windsurf     │                      │ • Workspace (.cursor)   │
         │ • Cline / Roo Code      │                      │ • Workspace (.clinerules│
         │ • VS Code Native        │                      │ • Workspace (.agents)   │
         └─────────────────────────┘                      └─────────────────────────┘
```

---

## 5. Directory Layout

```
skill_manager/
├── .agents/skills/               # Autonomous AI agent playbooks
│   └── universal-skill-manager/  # USM Autonomous Agent integration skill
├── assets/                       # UI icons and brand assets
├── tests/                        # Comprehensive unit and integration test suite
│   ├── conftest.py
│   └── unit/
│       ├── test_adapters.py
│       ├── test_agent_features.py
│       ├── test_cli.py
│       ├── test_health.py
│       ├── test_jsonio.py
│       ├── test_mcp_server.py
│       ├── test_merge.py
│       ├── test_portability.py
│       ├── test_prompt_skills.py
│       ├── test_verify.py
│       └── test_web.py
├── usm/                          # Python package source
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                    # Typer command-line interface
│   ├── models.py                 # Pydantic v2 data models
│   ├── registry.py               # Skills database manager
│   ├── settings.py               # Application configuration
│   ├── utils.py                  # Process, network, and system utilities
│   ├── adapters/                 # Client adapters
│   │   ├── antigravity.py
│   │   ├── base.py               # Base adapter and 3-way merge logic
│   │   ├── claude_code.py
│   │   ├── claude_desktop.py
│   │   ├── cline.py
│   │   ├── codex.py              # OpenAI Codex TOML engine
│   │   ├── cursor.py
│   │   ├── dynamic.py            # Dynamic custom AI client adapter
│   │   ├── roo_code.py
│   │   ├── vscode_native.py
│   │   └── windsurf.py
│   ├── compat/                   # Compatibility profiles
│   │   ├── discovery.py
│   │   ├── profile_model.py
│   │   └── profiles/             # Client TOML profiles
│   ├── core/                     # Core business logic
│   │   ├── engine.py             # Transaction executor
│   │   ├── health.py             # Server diagnostic engine
│   │   ├── journal.py            # Audit transaction log
│   │   ├── merge.py              # 3-Way merge algorithm
│   │   ├── planner.py            # Diff and execution planner
│   │   ├── portability.py        # .usmpack export/import
│   │   ├── prompt_engine.py      # Instruction/rule skill deployer
│   │   ├── scanner.py            # AI ecosystem discovery & auto-detection engine
│   │   ├── service.py            # Unified application service
│   │   ├── templates.py          # Ready-to-use MCP server templates
│   │   └── verify.py             # Post-write syntax verifier
│   ├── i18n/                     # Internationalization catalog
│   │   ├── __init__.py
│   │   └── locales/
│   │       └── en.json           # English localization strings
│   ├── io/                       # File system I/O primitives
│   │   ├── backup.py             # Timestamped backup manager
│   │   ├── jsonio.py             # Atomic read/write/verify
│   │   └── lock.py               # Multi-process file locks
│   ├── mcp/                      # Native MCP server implementation
│   │   └── server.py
│   └── web/                      # FastAPI Web Dashboard
│       ├── api.py
│       ├── server.py
│       └── static/               # HTML/CSS/JS frontend
├── ARCHITECTURE.md               # Architecture documentation
├── CONTRIBUTING.md               # Contributor guidelines
├── LICENSE                       # MIT License
├── README.md                     # Project overview and user manual
├── install.bat                   # One-click Windows installer
├── install.sh                    # One-click Unix installer
├── pyproject.toml                # PEP 517/621 packaging metadata
├── start_usm.bat                 # One-click Windows dashboard launcher
└── start_usm.sh                  # One-click Unix dashboard launcher
```

---

## 6. Data Models & Schema

### 6.1 Skill
A managed entity representing either an executable MCP server or a prompt-based agent skill:
```python
class Skill(BaseModel):
    id: str
    name: str
    description: str = ""
    kind: Literal["mcp_server", "agent_skill"] = "mcp_server"
    transport: Transport = Transport.STDIO
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    cwd: Optional[str] = None
    url: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    targets: Union[Literal["all"], List[TargetBinding]] = "all"
    platforms: Dict[str, PlatformOverride] = Field(default_factory=dict)
    enabled: bool = True
    tags: List[str] = Field(default_factory=list)
    content: Optional[str] = None  # Markdown rules for agent_skill
    scope: Literal["auto", "workspace", "global"] = "auto"
```

### 6.2 Plan & Operations
An execution plan containing granular operations for each client:
```python
class OpKind(str, Enum):
    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"
    NOOP = "noop"

class ClientPlan(BaseModel):
    client_id: str
    config_path: Path
    ops: List[Operation]
    clean: bool

class Plan(BaseModel):
    id: str
    created_at: datetime
    clients: Dict[str, ClientPlan]
```

### 6.3 Transaction & Audit
Every applied change is recorded with timestamped backups:
```python
class Transaction(BaseModel):
    id: str
    created_at: datetime
    plan_id: str
    status: Literal["applied", "rolled_back", "failed"]
    backups: Dict[str, str]  # client_id -> backup_file_path
    steps: List[Dict[str, Any]]
```

---

## 7. Central State & Registry

USM maintains its central state in `~/.skill-manager` (or portable `usm-data` if markers exist):
- `skills.json`: Registered skills, server configs, and target bindings.
- `settings.json`: System preferences, approval modes, backup policies.
- `state/<client_id>.json`: Fingerprints of managed entries per client to resolve 3-way merges.
- `backups/`: Timestamped pre-write backup snapshots.
- `journal/`: Transaction audit log files.
- `usm.lock`: File lock ensuring inter-process safety.

---

## 8. Client Adapters & Compatibility Layer

### 8.1 Adapter Responsibilities
Each client adapter implements:
1. **Detection:** Checks whether the client binary or default configuration directories exist.
2. **Config Reading:** Parses target configuration (JSON, JSONC, TOML).
3. **Config Writing:** Formats output maintaining comments and layout, performing atomic replacement.
4. **Merge Logic:** Merges USM-managed keys without deleting user-created tools.

### 8.2 Supported Clients Matrix
| Client ID | Platform | Default Path | Format | Tools Root |
|-----------|----------|--------------|--------|------------|
| `codex` | Win/Mac/Linux | `~/.codex/config.toml` | TOML | `mcp_servers` |
| `antigravity` | Win/Mac/Linux | `~/.gemini/antigravity-ide/mcp_config.json` | JSON | `mcpServers` |
| `claude_desktop` | Win/Mac/Linux | `~/.claude/claude_desktop_config.json` | JSON | `mcpServers` |
| `claude_code` | Win/Mac/Linux | `~/.claude/skills` / `.claude/skills` | Markdown | Skills |
| `cursor` | Win/Mac/Linux | `.cursor/rules/` | MDC | Rules |
| `windsurf` | Win/Mac/Linux | `~/.codeium/windsurf/mcp_config.json` | JSON | `mcpServers` |
| `cline` | Win/Mac/Linux | AppData / `.clinerules/` | JSON | `mcpServers` |
| `roo_code` | Win/Mac/Linux | AppData / `.clinerules/` | JSON | `mcpServers` |
| `vscode_native` | Win/Mac/Linux | `.vscode/mcp.json` | JSON | `mcpServers` |
| `custom` | Win/Mac/Linux | User-defined path | JSON/TOML | Dynamic (`--root-key`) |

### 8.3 Dynamic Client Registration & AI Ecosystem Scanner
- **Dynamic Registration (`DynamicClientAdapter`):** Enables connecting any newly installed AI assistant, terminal agent, or local runtime (e.g. Continue.dev, Zed, LM Studio) dynamically without writing code. Settings are saved in `settings.clients` and loaded automatically by `get_all_adapters()`.
- **Ecosystem Scanner (`AIScanner`):** Inspects the host workstation for installed AI assistants, background runtimes (Ollama, LM Studio), consumer shells (Google Gemini Desktop App), and running processes. Provides instant feedback and actionable recommendations via `usm scan` and MCP tool `usm_scan_clients`.

---

## 9. Synchronization Engine

```
[Registry State] + [Local Client Files] + [Previous Fingerprints]
                         │
                         ▼
             [3-Way Merge & Planner]
                         │
                         ▼
                 [Execution Plan]
                 (Dry-Run Preview)
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
   [Approved]                        [Cancelled]
        │
        ├─► 1. Pre-Write Timestamped Backup
        ├─► 2. Atomic Temp Write + Lock
        ├─► 3. Syntax & Structural Verify
        ├─► 4. Replace Original File
        ├─► 5. Commit to Journal
        └─► (If error: Auto-Rollback to Backup)
```

---

## 10. Safety Invariants & Non-Destructive Merging

### 10.1 3-Way Merge Algorithm
When USM synchronizes a client configuration:
1. **Base (Fingerprints):** What USM wrote during the previous sync.
2. **Local (Target File):** Current content of the client configuration file.
3. **Remote (Registry):** Current desired state in USM.

- If a tool exists in `Local` but not in `Base`, it is a **user-created tool** and is preserved.
- If a tool exists in `Base` but was deleted in `Local`, USM respects the user deletion or prompts based on drift settings.
- If a tool exists in `Remote` and is assigned to the client, it is injected or updated.

---

## 11. User Interfaces

### 11.1 Command Line Interface (CLI)
Built with `Typer` and `Rich`:
- `usm status [--json]`
- `usm list [--json]`
- `usm add <id> [--cmd <cmd>] [--template <tmpl>] [--kind prompt] [--content <txt>]`
- `usm remove <id>`
- `usm sync [--client <id>] [--json]`
- `usm undo [tx_id]`
- `usm setup-agent`
- `usm ui [--port 8765]`

### 11.2 Web Dashboard
A local, lightweight, dependency-free single-page dashboard:
- Fast status glance with connection health.
- Quick templates (GitHub, SQLite, Filesystem, Brave, Code Review, ADR).
- Immediate synchronization and undo buttons.
- Real-time client configuration path overrides.

---

## 12. Autonomous Agent Enablement

USM exposes a native Model Context Protocol (MCP) server so that AI agents (Antigravity, Codex, Claude, Cursor) can manage environment tools autonomously:
- `usm_status`: Probe client discovery and runtime status.
- `usm_list_skills`: Query active skills and server configurations.
- `usm_add_mcp_server`: Install and configure an executable tool across clients.
- `usm_add_prompt_skill`: Deploy a Markdown prompt instruction rule.
- `usm_remove_skill`: Unlink and delete a tool.
- `usm_sync_all`: Trigger cross-client synchronization.
- `usm_undo`: Rollback the last operation.

---

## 13. Portability & Profiles (`.usmpack`)

The portability subsystem packages registries, settings, and agent skills into a single portable zip archive (`.usmpack`):
- `metadata.json`: Timestamp, export version, host platform.
- `skills.json`: Complete registry snapshot.
- `settings.json`: Configured preferences.
- `prompt_skills/`: Exported Markdown rule files.

---

## 14. Security, Sandboxing & Secrets Handling

1. **Local Isolation:** The Web UI and API bind strictly to `127.0.0.1` by default.
2. **Environment Variable Expansion:** Supports `$VAR` and `%VAR%` syntax so API tokens are not stored in plain text.
3. **Command Sanitization:** Windows executable shims (`cmd /c`) are applied safely to prevent command-injection vulnerabilities.

---

## 15. Health Checking & Self-Healing

The health monitoring engine assesses configured MCP servers:
- **Executable Existence:** Verifies command binary is in PATH or exists locally.
- **Syntax Check:** Validates JSON/TOML configuration syntax.
- **Port Probe:** Tests connectivity for HTTP/SSE servers.

---

## 16. Daemon & Drift Detection

An optional background file-watcher (`watchdog`) can detect manual edits to client configuration files and warn of drift, maintaining consistency without unexpected overwrites.

---

## 17. Diagnostics & Error Hierarchy

USM defines standardized error codes:
- `E1001`: Validation Error (invalid options or schemas).
- `E2001`: Config File Not Found.
- `E2003`: Parse Error (corrupt JSON/TOML).
- `E3001`: Ambiguous Configuration Paths.
- `E4001`: Post-write Verification Failure (triggers automated rollback).

---

## 18. Testing & Verification Strategy

The test suite achieves comprehensive coverage across all subsystems:
- **Unit Tests:** Adapters, 3-way merge, prompt deployment, JSON I/O, health checking.
- **CLI Tests:** Command invocation, argument parsing, JSON output mode.
- **Web API Tests:** FastAPI routes, settings updates, sync triggers.
- **MCP Server Tests:** Tool registration and dispatch via `anyio`.

---

## 19. Roadmap

- [x] v0.1.0: Core engine, profile adapters, 3-way merge, Web UI, CLI, MCP Server.
- [x] v0.2.0: OpenAI Codex & VS Code ChatGPT TOML adapter integration, global prompt skill deployment.
- [ ] v0.3.0: Cloud registry sync (optional GitHub Gist / S3 profile synchronization).
- [ ] v0.4.0: Desktop tray companion app with system notification toasts.
