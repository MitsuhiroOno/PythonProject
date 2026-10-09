import importlib.util
import json
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "plugins" / "reasoning_boost" / "__init__.py"
_spec = importlib.util.spec_from_file_location("reasoning_boost", _path)
rb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rb)


def test_think_tool_returns_json():
    assert json.loads(rb.think({"thought": "abc"})) == {"ok": True, "chars": 3}


def test_hook_injects_only_for_complex_turns(monkeypatch):
    monkeypatch.delenv("HERMES_REASONING_BOOST", raising=False)
    assert rb.on_pre_llm_call(user_message="こんにちは") is None
    assert rb.on_pre_llm_call(user_message="この関数のバグを調査して")["context"] == rb.REMINDER
    assert rb.on_pre_llm_call(user_message=[{"type": "text", "text": "Compute 2^10"}]) is not None


def test_hook_can_be_disabled(monkeypatch):
    monkeypatch.setenv("HERMES_REASONING_BOOST", "off")
    assert rb.on_pre_llm_call(user_message="compute this") is None


def test_register_wires_tool_and_hook():
    calls = []

    class Ctx:
        def register_tool(self, **kw):
            calls.append(("tool", kw["name"], kw["toolset"]))

        def register_hook(self, name, cb):
            calls.append(("hook", name, cb))

    rb.register(Ctx())
    assert ("tool", "think", "reasoning") in calls
    assert ("hook", "pre_llm_call", rb.on_pre_llm_call) in calls
