from pathlib import Path
from usm.adapters.base import ProfileDrivenAdapter

class ClaudeDesktopAdapter(ProfileDrivenAdapter):
    def __init__(self):
        profile_path = Path(__file__).parent.parent / "compat" / "profiles" / "claude_desktop.toml"
        super().__init__(profile_path)
