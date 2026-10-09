"""reasoning_boost — Hermes Agent plugin.

* ``think`` tool: a no-op scratchpad that gives the model a place to reason
  about tool results mid-loop (the "think tool" pattern).
* ``pre_llm_call`` hook: on turns that look complex, appends a short
  plan-then-verify reminder to the user message.

Set ``HERMES_REASONING_BOOST=off`` to disable the hook without uninstalling
(handy for A/B runs in ``evals/``).
"""

import json
import os
import re

THINK_SCHEMA = {
    "name": "think",
    "description": (
        "Think step by step without taking any action or fetching new data. "
        "Use it after a tool result to check whether it answers the question, "
        "to list remaining requirements, or to choose the next step. "
        "The thought is only logged; nothing in the environment changes."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "thought": {"type": "string", "description": "Your reasoning."},
        },
        "required": ["thought"],
    },
}

REMINDER = (
    "[reasoning_boost] Before answering: (1) list the requirements of this "
    "request, (2) plan briefly, (3) compute or check facts with tools rather "
    "than from memory, (4) verify the final answer a second way."
)

_COMPLEX_HINTS = re.compile(
    r"(計算|証明|設計|比較|手順|なぜ|最適|バグ|調査|"
    r"calculate|compute|prove|design|compare|debug|optimi[sz]e|why|plan|step)",
    re.IGNORECASE,
)


def think(args: dict, **kwargs) -> str:
    thought = str(args.get("thought", ""))
    return json.dumps({"ok": True, "chars": len(thought)})


def _text(user_message) -> str:
    if isinstance(user_message, str):
        return user_message
    if isinstance(user_message, list):
        return " ".join(
            p.get("text", "") for p in user_message if isinstance(p, dict)
        )
    return ""


def looks_complex(text: str) -> bool:
    if len(text) >= 280:
        return True
    if text.count("?") + text.count("?") >= 2:
        return True
    if len(re.findall(r"^\s*(?:[-*]|\d+[.)])\s", text, re.MULTILINE)) >= 2:
        return True
    return bool(_COMPLEX_HINTS.search(text))


def on_pre_llm_call(user_message=None, **kwargs):
    if os.environ.get("HERMES_REASONING_BOOST", "").lower() in {"0", "off", "false"}:
        return None
    if looks_complex(_text(user_message)):
        return {"context": REMINDER}
    return None


def register(ctx):
    ctx.register_tool(
        name="think",
        toolset="reasoning",
        schema=THINK_SCHEMA,
        handler=think,
        description="Scratchpad for step-by-step reasoning",
        emoji="🧠",
    )
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
