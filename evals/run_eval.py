"""Hermes Agent の設定違い(variant)を同じタスクセットで比較する評価スクリプト。

各タスクを `hermes chat -q <prompt> -Q` で非対話実行し、応答の最後の
`FINAL: <answer>` 行を正解と照合する。標準ライブラリのみで動く。

例:
    python evals/run_eval.py --dry-run
    python evals/run_eval.py --variants baseline,boost --repeat 2 --workers 4
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent

ANSWER_INSTRUCTION = (
    "\n\nWhen you are done, put the final answer alone on the last line "
    "in the form `FINAL: <answer>` (no units, no extra words)."
)

_FINAL_RE = re.compile(r"FINAL:\s*`?([^`\n]+?)`?\s*$", re.MULTILINE)
_NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?|-?\.\d+")


def load_tasks(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_variants(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def extract_final(output):
    matches = _FINAL_RE.findall(output or "")
    return matches[-1].strip() if matches else None


def _to_number(text):
    m = _NUMBER_RE.search(text.replace("$", ""))
    return float(m.group().replace(",", "")) if m else None


def grade(task, final):
    if final is None:
        return False
    kind = task.get("type", "exact")
    expected = task["answer"]
    if kind == "number":
        got, want = _to_number(final), float(expected)
        return got is not None and abs(got - want) <= max(1e-9, abs(want) * 1e-6)
    if kind == "regex":
        return re.fullmatch(expected, final.strip(), re.IGNORECASE) is not None
    return final.strip().strip(".").lower() == str(expected).strip().lower()


def build_command(hermes_bin, profile, task, variant):
    cmd = [hermes_bin]
    if profile:
        cmd += ["-p", profile]
    cmd += ["chat", "-q", task["prompt"] + ANSWER_INSTRUCTION, "-Q"]
    return cmd + list(variant.get("args", []))


def run_one(hermes_bin, profile, timeout, variant_name, variant, task, attempt):
    cmd = build_command(hermes_bin, profile, task, variant)
    env = {**os.environ, **{k: str(v) for k, v in variant.get("env", {}).items()}}
    start = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              env=env, stdin=subprocess.DEVNULL)
        output, error = proc.stdout, (proc.stderr[-2000:] if proc.returncode else None)
    except subprocess.TimeoutExpired:
        output, error = "", f"timeout after {timeout}s"
    except FileNotFoundError:
        output, error = "", f"{hermes_bin!r} not found"
    final = extract_final(output)
    return {
        "variant": variant_name, "task": task["id"], "category": task.get("category", ""),
        "attempt": attempt, "final": final, "expected": task["answer"],
        "correct": grade(task, final), "seconds": round(time.monotonic() - start, 1),
        "error": error, "output_tail": output[-1500:],
    }


def summarize(results):
    by_variant = defaultdict(list)
    for r in results:
        by_variant[r["variant"]].append(r)
    categories = sorted({r["category"] for r in results})
    header = ["variant", "accuracy", *categories, "avg_sec", "errors"]
    rows = []
    for name, rs in by_variant.items():
        acc = sum(r["correct"] for r in rs) / len(rs)
        cats = []
        for c in categories:
            cr = [r for r in rs if r["category"] == c]
            cats.append(f"{sum(r['correct'] for r in cr)}/{len(cr)}" if cr else "-")
        avg = sum(r["seconds"] for r in rs) / len(rs)
        errors = sum(1 for r in rs if r["error"])
        rows.append([name, f"{acc:.0%}", *cats, f"{avg:.1f}", str(errors)])
    widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    return "\n".join([fmt.format(*header)] + [fmt.format(*row) for row in rows])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tasks", default=str(HERE / "tasks.jsonl"))
    p.add_argument("--variants-file", default=str(HERE / "variants.json"))
    p.add_argument("--variants", help="カンマ区切りで実行する variant を絞る")
    p.add_argument("--only", help="カンマ区切りでタスク id かカテゴリを絞る")
    p.add_argument("--repeat", type=int, default=1, help="各タスクの試行回数(ばらつき対策)")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--hermes-bin", default="hermes")
    p.add_argument("--profile", help="hermes -p <profile> で実行する")
    p.add_argument("--out", default=str(HERE / "results"))
    p.add_argument("--dry-run", action="store_true", help="実行せずコマンドだけ表示")
    args = p.parse_args(argv)

    tasks = load_tasks(args.tasks)
    if args.only:
        keep = set(args.only.split(","))
        tasks = [t for t in tasks if t["id"] in keep or t.get("category") in keep]
    variants = load_variants(args.variants_file)
    if args.variants:
        names = args.variants.split(",")
        unknown = [n for n in names if n not in variants]
        if unknown:
            p.error(f"unknown variants: {', '.join(unknown)}")
        variants = {n: variants[n] for n in names}

    jobs = [(vn, v, t, a) for vn, v in variants.items() for t in tasks for a in range(args.repeat)]
    if args.dry_run:
        for vn, v, t, _ in jobs:
            env = " ".join(f"{k}={val}" for k, val in v.get("env", {}).items())
            print(f"[{vn}] {env} {subprocess.list2cmdline(build_command(args.hermes_bin, args.profile, t, v))}")
        return 0

    print(f"running {len(jobs)} jobs ({len(variants)} variants x {len(tasks)} tasks x {args.repeat})",
          file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, args.hermes_bin, args.profile, args.timeout, *job) for job in jobs]
        results = []
        for f in futures:
            r = f.result()
            mark = "OK " if r["correct"] else "NG "
            print(f"{mark}[{r['variant']}] {r['task']}: got={r['final']!r} want={r['expected']!r}"
                  + (f" ({r['error'][:80]})" if r["error"] else ""), file=sys.stderr)
            results.append(r)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"run-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(summarize(results))
    print(f"\ndetails: {out_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
