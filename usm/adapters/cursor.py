from pathlib import Path
from usm.adapters.base import ProfileDrivenAdapter

class CursorAdapter(ProfileDrivenAdapter):
    def __init__(self):
        profile_path = Path(__file__).parent.parent / "compat" / "profiles" / "cursor.toml"
        super().__init__(profile_path)
