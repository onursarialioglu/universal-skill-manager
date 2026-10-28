from usm.core.merge import compute_3way_merge
from usm.models import ManagedEntry, OpKind

def test_3way_merge_add_and_preserve_unmanaged():
    client_id = "claude-desktop"
    base = {}
    local = {
        "user_custom_server": {"command": "node", "args": ["custom.js"]}
    }
    desired = {
        "github": {"command": "npx", "args": ["@modelcontextprotocol/server-github"]}
    }

    ops, final_servers = compute_3way_merge(client_id, base, local, desired)

    # 1. Operation is ADD for github
    assert len(ops) == 1
    assert ops[0].kind == OpKind.ADD
    assert ops[0].server_name == "github"

    # 2. Invariant: unmanaged server must remain intact in final_servers!
    assert "user_custom_server" in final_servers
    assert final_servers["user_custom_server"] == {"command": "node", "args": ["custom.js"]}
    assert "github" in final_servers

def test_3way_merge_remove():
    client_id = "claude-desktop"
    base = {
        "github": ManagedEntry(native_name="github", content_hash="abc", rendered={"command": "npx"}, tx_id="tx_1")
    }
    local = {
        "github": {"command": "npx"},
        "user_custom": {"command": "uvx"}
    }
    desired = {}  # github was removed

    ops, final_servers = compute_3way_merge(client_id, base, local, desired)

    assert len(ops) == 1
    assert ops[0].kind == OpKind.REMOVE
    assert ops[0].server_name == "github"
    assert "github" not in final_servers
    assert "user_custom" in final_servers  # unmanaged untouched!

def test_3way_merge_idempotency():
    client_id = "claude-desktop"
    base = {
        "github": ManagedEntry(
            native_name="github",
            content_hash="6e554b5dfd475a363d6b1d120a8c2f1f0a8cbb42bfb588db62332be1947b97c4",
            rendered={"command": "npx", "args": ["test"]},
            tx_id="tx_1"
        )
    }
    local = {
        "github": {"command": "npx", "args": ["test"]}
    }
    desired = {
        "github": {"command": "npx", "args": ["test"]}
    }

    from usm.utils import compute_json_hash
    base["github"].content_hash = compute_json_hash(desired["github"])

    ops, final_servers = compute_3way_merge(client_id, base, local, desired)
    assert len(ops) == 1
    assert ops[0].kind == OpKind.NOOP
