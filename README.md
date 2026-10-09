# PythonProject — Hermes Agent を賢くする実験キット

[Nous Research の Hermes Agent](https://github.com/NousResearch/hermes-agent) を対象に、
**推論・計画の質**と**ツール連携**を強化する手を入れ、**評価スクリプトで効果を比較**するためのキットです。

| 場所 | 内容 | 効く方向 |
|---|---|---|
| `hermes_home/config.snippet.yaml` | 推論量・MoA・サブエージェント・ループ防止・MCP の設定例 | 推論 / ツール |
| `hermes_home/SOUL.md` | 「計画 → ツールで確認 → 検証してから回答」の作業スタイル | 推論 |
| `skills/deliberate-planning/` | 複雑なタスクを検証可能な計画に分解するスキル | 計画 |
| `skills/verify-before-answer/` | 回答前の検証チェックリストのスキル | 推論 |
| `plugins/reasoning_boost/` | `think` スクラッチパッドツールと、複雑な依頼で計画・検証を促す `pre_llm_call` フック | 推論 / ツール |
| `evals/` | 設定違い(variant)を同じ問題で比較する評価ハーネス | 評価 |

## セットアップ

```bash
# Hermes Agent 本体(未導入の場合)
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

git clone <this repo> ~/PythonProject && cd ~/PythonProject

# 1. 設定: hermes_home/config.snippet.yaml の内容を ~/.hermes/config.yaml にマージ
#    (skills.external_dirs のパスは clone した場所に合わせる)
# 2. SOUL.md: 既存の ~/.hermes/SOUL.md があればバックアップしてから
cp hermes_home/SOUL.md ~/.hermes/SOUL.md
# 3. プラグイン
ln -s "$PWD/plugins/reasoning_boost" ~/.hermes/plugins/reasoning_boost
hermes plugins enable reasoning_boost
```

`moa.presets` と `mcp_servers` のモデル名・サーバーは例です。手元で使えるプロバイダ/モデルに書き換えてください。

## 評価で効果を測る

`evals/tasks.jsonl` は答えが一意に決まる13問です。

- `reasoning`(7問): 引っかけのある推論問題(バットとボール、カタツムリ、など)
- `tool`(6問): 暗算では無理で、コード実行などのツールを使えば確実に解ける問題(素数和、SHA-256、など)

`evals/variants.json` で比較する設定を定義します。

| variant | 中身 |
|---|---|
| `baseline` | `--reasoning low`、プラグインのフック無効 |
| `high-reasoning` | `--reasoning high` のみ |
| `boost` | high + `reasoning_boost` フック |
| `boost+skills` | 上記 + 2スキルを事前ロード |
| `moa` | Mixture of Agents プリセット `deep` |

```bash
python evals/run_eval.py --dry-run                         # 実行コマンドの確認
python evals/run_eval.py --variants baseline,boost --repeat 3 --workers 4
python evals/run_eval.py --only tool                       # カテゴリやタスク id で絞り込み
```

各タスクを `hermes chat -q ... -Q` で非対話実行し、最後の `FINAL: <answer>` 行を採点します。
結果は variant ごとの正答率・カテゴリ別スコア・平均秒数の表で出力し、詳細は `evals/results/*.jsonl` に保存します。
LLM の出力はばらつくので、比較するときは `--repeat 3` 以上をおすすめします。

SOUL.md の有無など、プロファイル単位で切り替えたい差分は `hermes profile create <name>` で別プロファイルを作り、
`--profile <name>` を付けて実行してください。

### 問題を増やす

`tasks.jsonl` に1行1問で追加します。`type` は `number`(数値で比較、カンマや `$` は無視)、
`exact`(大文字小文字を無視した完全一致)、`regex` のいずれかです。

## テスト

```bash
pip install pytest
python -m pytest -q tests
```

評価スクリプトの採点ロジックとプラグインを、Hermes 本体なしでテストします。
