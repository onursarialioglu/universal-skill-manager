import pytest
from usm.adapters import get_adapter
from usm.core.verify import verify_write, VerificationError
from usm.io.jsonio import write_json_atomic
from usm.models import OpKind, PlannedOp

def test_verify_detects_removed_unmanaged_server(tmp_path):
    f = tmp_path / "config.json"
    adapter = get_adapter("claude-desktop")

    before_raw = {
        "mcpServers": {
            "user_custom": {"command": "node", "args": ["custom.js"]}
        }
    }
    # after_raw accidentally wiped out user_custom
    after_raw = {
        "mcpServers": {
            "new_server": {"command": "npx", "args": ["pkg"]}
        }
    }
    write_json_atomic(f, after_raw)

    ops = [
        PlannedOp(
            client_id="claude-desktop",
            server_name="new_server",
            kind=OpKind.ADD,
            reason_key="plan.reason.new_target"
        )
    ]

    with pytest.raises(VerificationError) as exc_info:
        verify_write(adapter, f, ops, before_raw, after_raw)
    assert "Unmanaged server 'user_custom' was removed" in str(exc_info.value)
