from pathlib import Path
from usm.adapters.base import ProfileDrivenAdapter

class VSCodeNativeAdapter(ProfileDrivenAdapter):
    def __init__(self):
        profile_path = Path(__file__).parent.parent / "compat" / "profiles" / "vscode_native.toml"
        super().__init__(profile_path)
