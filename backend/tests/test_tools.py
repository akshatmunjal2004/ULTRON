import pytest

from app.tools.file_ops import FileOpsTool, resolve_in_workspace
from app.tools.open_url import OpenUrlTool
from app.tools.registry import get_registry


def test_tool_list_is_exposed(client):
    res = client.get("/api/v1/tools")
    assert res.status_code == 200
    names = {t["name"] for t in res.json()["tools"]}
    assert {"web_search", "memory_tool", "file_ops", "code_runner"} <= names


def test_unknown_tool_is_a_404(client):
    res = client.post("/api/v1/tools/execute", json={"tool": "nope", "args": {}})
    assert res.status_code == 404


def test_schemas_are_generated_from_pydantic_models():
    schema = get_registry().get("web_search").json_schema()
    params = schema["function"]["parameters"]
    assert params["required"] == ["query"]
    assert params["properties"]["max_results"]["maximum"] == 10


def test_bad_arguments_are_reported_not_raised():
    result = get_registry().execute("web_search", {"max_results": 99})
    assert result.ok is False
    assert "Invalid arguments" in result.result


@pytest.mark.parametrize(
    "path",
    ["../secrets.txt", "/etc/passwd", "../../etc/passwd", "sub/../../out.txt"],
)
def test_workspace_escape_is_blocked(path):
    with pytest.raises(ValueError):
        resolve_in_workspace(path)


def test_sibling_directory_prefix_is_blocked(tmp_path, monkeypatch):
    # The old startswith() check let `workspace-notes` pass as `workspace`.
    from app.core.config import settings

    root = tmp_path / "workspace"
    root.mkdir()
    (tmp_path / "workspace-notes").mkdir()
    monkeypatch.setattr(settings, "WORKSPACE_DIR", root)
    with pytest.raises(ValueError):
        resolve_in_workspace("../workspace-notes/leak.txt")


def test_file_round_trip():
    tool = FileOpsTool()
    assert "Wrote" in tool.run({"action": "write", "filename": "note.txt", "content": "hi"}).result
    assert tool.run({"action": "read", "filename": "note.txt"}).result == "hi"
    assert "note.txt" in tool.run({"action": "list"}).result
    assert "Deleted" in tool.run({"action": "delete", "filename": "note.txt"}).result


def test_open_url_refuses_internal_hosts():
    tool = OpenUrlTool()
    assert tool.run({"url": "http://169.254.169.254/latest/meta-data"}).ok is False
    assert tool.run({"url": "example.com"}).result == "OPEN_URL::https://example.com"


def test_code_runner_captures_output_and_timeouts():
    tool = get_registry().get("code_runner")
    assert tool.run({"code": "print(2 + 2)"}).result == "4"
    slow = tool.run({"code": "while True: pass"})
    assert "stopped" in slow.result
