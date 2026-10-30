# Contributing to Universal Skill Manager (USM)

Thank you for your interest in contributing to **Universal Skill Manager**! We welcome contributions from developers and AI practitioners of all backgrounds.

---

## Code of Conduct

Please maintain a respectful, constructive, and collaborative tone in all discussions, issues, and pull requests.

---

## Development Setup

1. **Fork and Clone** the repository:
   ```bash
   git clone https://github.com/onursarialioglu/universal-skill-manager.git
   cd universal-skill-manager
   ```

2. **Create a Virtual Environment**:
   ```bash
   # Windows:
   python -m venv .venv
   # Linux / macOS:
   python3 -m venv .venv
   ```

3. **Install in Editable Mode with Dev Dependencies**:
   ```bash
   # Windows:
   .\.venv\Scripts\pip install -e ".[all]"
   # Linux / macOS:
   ./.venv/bin/pip install -e ".[all]"
   ```

4. **Run Test Suite**:
   ```bash
   # Windows:
   .\.venv\Scripts\pytest -v
   # Linux / macOS:
   ./.venv/bin/pytest -v
   ```

---

## Core Invariants & Contribution Rules

When contributing code, you **must** preserve these core invariants:

1. **3-Way Merge Safety**:
   - Never unconditionally overwrite client configuration files.
   - Any manual or unmanaged MCP servers configured by the user must be preserved.

2. **Atomic Writes & Backups**:
   - Every file change must create a timestamped backup (`.bak_<timestamp>`) before writing.
   - Use atomic write techniques (temporary file rename with file locking).

3. **Post-Write Verification**:
   - After updating any JSON config file, read it back and verify it is valid JSON and contains all unchanged data bit-for-bit intact.

4. **Multi-Client Portability**:
   - Use client adapters (`usm.adapters`) and profiles (`usm.compat.profiles`).
   - Wrap Windows commands properly (`cmd /c npx ...`).

5. **100% Test Coverage for Adapters & MCP Tools**:
   - Always add unit tests under `tests/unit/` for new adapters, features, or CLI commands.
   - All tests must pass cleanly before opening a pull request.

---

## Pull Request Process

1. Create a descriptive branch: `git checkout -b feature/my-new-feature`.
2. Commit with clear, concise messages.
3. Ensure `pytest` passes with 100% green tests.
4. Push your branch and open a Pull Request describing your changes and motivations.
