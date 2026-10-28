import json
import pytest
from usm.io.jsonio import read_json, write_json_atomic, detect_format

def test_atomic_write_and_read(tmp_path):
    f = tmp_path / "test.json"
    data = {"mcpServers": {"test": {"command": "echo", "args": ["hello"]}}}
    
    write_json_atomic(f, data)
    assert f.exists()

    loaded, fmt = read_json(f)
    assert loaded == data
    assert fmt.indent == 2

def test_preserves_indent_and_newlines(tmp_path):
    f = tmp_path / "indent4.json"
    raw_content = '{\n    "key": "value"\n}\n'
    f.write_text(raw_content, encoding="utf-8")

    loaded, fmt = read_json(f)
    assert fmt.indent == 4

    loaded["key2"] = "value2"
    write_json_atomic(f, loaded, fmt=fmt)

    written_text = f.read_text(encoding="utf-8")
    assert "    " in written_text

def test_read_non_dict_fails(tmp_path):
    f = tmp_path / "array.json"
    f.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ValueError):
        read_json(f)
