# docs/CHANGELOG.md

`skills/unity-ugui-runtime-ui/SKILL.md` の `metadata.version` と一致させる。バージョニングの粒度は `requirements.md` 13.1節に従う：`description` の変更・手順の分岐追加は**マイナー**、不変条件の追加・出力構造の変更は**メジャー**、文言修正は**パッチ**。Gitタグはバージョンと一致させ（例：`01.01.00`）、注釈付きタグ（`git tag -a`）とする。

---

## [0.1.0] — 初版リリース

`metadata.version: 0.1.0`（`skills/unity-ugui-runtime-ui/SKILL.md`）に対応。

### 追加

- `SKILL.md`：`name`・`description`・F0〜F7の手順骨格、不変条件12項目、参照ファイルの読み込み条件、出力構造。
- `references/`：`layout.md`・`components.md`・`ux-checklist.md`・`text-and-fonts.md`・`webgl-runtime.md`・`review-rubric.md`（6ファイル）。
- `scripts/`：`lint_ugui_csharp.py`・`check_contrast.py`・`unity_batch_compile.py`（Python 3標準ライブラリのみで動作）。
- `assets/`：`UiTheme.cs.tmpl`・`UiFactory.cs.tmpl`・`UiScreenBase.cs.tmpl`・`UiResolutionSweepTests.cs.tmpl`・`UiBatchCompileCheck.cs.tmpl`・`report-template.md`（6点）。
- `tests/prompts/`・`tests/expected/`：発火・構築、発火・改修、発火・レビュー、発火・部分適用、非発火、前提欠落、参照未読の7類型の対応表。
- `tests/scripts/`：`scripts/` 各Pythonスクリプトの単体テスト。
- `.github/workflows/ci.yml`：フロントマター・命名検証（`skills-ref validate`）、`SKILL.md` 行数上限・参照ファイル目次有無の検証、参照ファイルへの相対リンク確認、禁止内容検査、`scripts/` 単体テスト、`.skill` パッケージ生成。
- `README.md`：スキル概要・対象範囲・対応ホストと設置先・開発フローの案内。
- 配布用symlink：`.claude/skills/unity-ugui-runtime-ui`・`.agents/skills`（`requirements.md` 12.2節）。
- `docs/spec.md`・`docs/hosts.md`・`docs/CHANGELOG.md`（本ファイル）の初版。

### 対象ホスト・Unityの再確認結果（13.1節）

- 対象バージョン表（`requirements.md` 1.5節）を参照日 2026年9月2日時点の一次情報で確認済み：Agent Skills標準（agentskills.io Specification）、Claude Code 2.1.258（2026-09-01）、Codex CLI 0.152.1（2026-09-01）、Antigravity 2.0（2026-05-19発表）、Unity 6.3 LTS（6.6を Supported Update として併記）。
- 設置先表（`requirements.md` 2.3節）を同日時点で確認済み。
- ホスト間の実行比較（`tests/prompts/` を3ホストで再実行しての発火可否・停止可否・出力構造一致確認、11.2節）は初版リリース時点では未実施。次回の月次監視（14章）で実施し、結果を `docs/hosts.md` に記録する。

### 既知の制限

- なし（`docs/hosts.md` を参照）。
