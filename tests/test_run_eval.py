import json
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

import run_eval  # noqa: E402


def test_extract_final_takes_last_line():
    out = "thinking...\nFINAL: 3\nwait, recheck\nFINAL: `47`\nsession: abc"
    assert run_eval.extract_final(out) == "47"
    assert run_eval.extract_final("no answer here") is None


def test_grade_number_exact_regex():
    num = {"answer": "234168", "type": "number"}
    assert run_eval.grade(num, "234,168")
    assert run_eval.grade({"answer": "0.05", "type": "number"}, "$0.05")
    assert not run_eval.grade(num, "234169")
    assert not run_eval.grade(num, None)
    assert run_eval.grade({"answer": "21e63e26eab4"}, "21E63E26EAB4.")
    assert run_eval.grade({"answer": r"1\s*sister", "type": "regex"}, "1 sister")


def test_task_file_is_well_formed():
    tasks = run_eval.load_tasks(run_eval.HERE / "tasks.jsonl")
    assert len({t["id"] for t in tasks}) == len(tasks)
    for t in tasks:
        assert t["prompt"] and t["answer"]
        if t.get("type") == "number":
            float(t["answer"])


def test_end_to_end_with_fake_hermes(tmp_path, capsys):
    fake = tmp_path / "hermes"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "print('working')\n"
        "print('FINAL: 5' if os.environ.get('HERMES_REASONING_BOOST') == 'on' else 'FINAL: 100')\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text(json.dumps({"id": "w", "category": "reasoning", "prompt": "p",
                                 "answer": "5", "type": "number"}) + "\n")
    rc = run_eval.main(["--tasks", str(tasks), "--variants", "baseline,boost",
                        "--hermes-bin", str(fake), "--out", str(tmp_path / "out")])
    assert rc == 0
    lines = (next((tmp_path / "out").glob("*.jsonl"))).read_text().splitlines()
    results = {json.loads(l)["variant"]: json.loads(l)["correct"] for l in lines}
    assert results == {"baseline": False, "boost": True}
    assert "boost" in capsys.readouterr().out
