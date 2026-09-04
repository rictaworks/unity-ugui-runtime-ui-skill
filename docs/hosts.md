# docs/hosts.md — ホスト別の設置・挙動差の記録

対象ホスト（Claude Code・Codex CLI・Antigravity）における設置先・実際の設置状況・挙動差を記録する。正は `requirements.md` 2.3節（対象ホストと設置先）・12.2節（設置）。設置先パスや挙動に変更が生じた場合は、まず `requirements.md` を改訂フロー（13.3節）に従って更新し、この文書はその結果を追随して記録する。

## 設置先一覧（requirements.md 2.3節）

`<name>` は `unity-ugui-runtime-ui`。

| ホスト | ワークスペース設置先 | グローバル設置先 | 明示呼び出し |
|---|---|---|---|
| Claude Code | `.claude/skills/<name>/` | `~/.claude/skills/<name>/` | `/unity-ugui-runtime-ui` |
| Codex CLI | `.agents/skills/<name>/` | `~/.agents/skills/<name>/` | `$unity-ugui-runtime-ui` |
| Antigravity | `.agents/skills/<name>/`（`.agent/skills/`も後方互換） | `~/.gemini/antigravity/skills/<name>/` | 会話中でスキル名に言及 |

設置先パスは参照日（`requirements.md` 1.5節）時点の一次情報・コミュニティ検証に基づく。改訂フロー（13.3節）で定期的に再確認する。

## 設置方法（requirements.md 12.2節）

リポジトリ本体（`skills/unity-ugui-runtime-ui/`）をSingle Source of Truthとし、各ホストのスキルディレクトリへはsymlinkで設置する。

| ホスト | 設置方法 |
|---|---|
| Claude Code | `.claude/skills/unity-ugui-runtime-ui` → `skills/unity-ugui-runtime-ui` のsymlink（スキル単位） |
| Codex CLI | `.agents/skills/unity-ugui-runtime-ui` → 同上のsymlink（Codexはsymlinkの参照先を辿る） |
| Antigravity | `.agents/skills` ディレクトリ自体を `skills/` へのsymlinkとする（スキル単位のsymlinkは検出されない事例があるため、ディレクトリ単位で行う）。グローバル設置は `~/.gemini/antigravity/skills` を同様にディレクトリ単位でsymlinkする |

CodexとAntigravityは同じ `.agents/skills` を読むため、ワークスペースでは `.agents/skills` をディレクトリ単位でsymlinkする方式に統一している（`unity-ugui-runtime-ui-skill` リポジトリの `.claude/skills/unity-ugui-runtime-ui` および `.agents/skills` として設置済み。設置元PR: symlink配布 #23）。

## 実機確認状況

| ホスト | ワークスペースsymlink | 参照先解決 | 明示呼び出しの確認 |
|---|---|---|---|
| Claude Code | `.claude/skills/unity-ugui-runtime-ui` を設置済み | `skills/unity-ugui-runtime-ui` に解決することを確認済み | 未実施（次回月次監視で確認） |
| Codex CLI | `.agents/skills`（ディレクトリ単位symlink）配下の `unity-ugui-runtime-ui` として到達可能 | `skills/` に解決することを確認済み | 未実施（次回月次監視で確認） |
| Antigravity | 同上（`.agents/skills` を共有） | 同上 | 未実施（次回月次監視で確認） |

グローバル設置（`~/.claude/skills/`・`~/.agents/skills/`・`~/.gemini/antigravity/skills/`）は各ツールへの設置作業（`requirements.md` 12.2節・13.3節5.：人間が行う）が発生した時点で追記する。

## ホスト間の挙動差

現時点（初版）では、`tests/prompts/` を用いたホスト間の実行比較（`requirements.md` 11.2節）が未実施のため、**既知の挙動差なし**として記録する。

月次監視（14章）または対象ホストのリリース後に `tests/prompts/` を3ホストで再実行し、以下を確認したら、その都度この節に追記する。

- 発火可否
- 停止可否
- 報告の見出し構造
- 生成ファイル名

挙動差が検出された場合の扱いは `requirements.md` 13.4節の方針に従う。

1. まず汎用コア（`SKILL.md`・`references`）は変更せず、`description` の語順・語彙で差を吸収できないか検討する。
2. 吸収できない差はホスト固有ラッパー（例：Codex向け `agents/openai.yaml`）として汎用コアの外に分離し、採用理由をこの文書に記す。
3. ラッパーでも解消しない差は既知の制限として `README.md` に記載し、そのホストでの明示呼び出し手順を案内する。

## 配布済みバージョンとの対応（requirements.md 13.2節）

リリースごとに `.skill` のハッシュを記録し、設置先の内容がどのリリースに対応するかを追跡する。初版リリース前のため、現時点では該当エントリなし。次回リリース以降、以下の形式で追記する。

| バージョン | `.skill` ハッシュ | 設置日 | 備考 |
|---|---|---|---|
| 0.1.0 | `sha256:9e453ae3aff69726883291da21228c27d95531852453f4ae120812492eaefe18` | 未設置 | [GitHub Release 0.1.0](https://github.com/rictaworks/unity-ugui-runtime-ui-skill/releases/tag/0.1.0) 添付の `unity-ugui-runtime-ui-0.1.0.skill`。各ホストへの設置（12.2節・13.3節5.）が行われた時点で「設置日」を追記する。**本番確認（2026-09-04）**：公開URLからダウンロードしSHA-256が上記と一致することを確認、展開して16ファイルの構成（`SKILL.md`・`assets/`6点・`references/`6点・`scripts/`3点）を確認、`scripts/`の3本（`lint_ugui_csharp.py`・`check_contrast.py`・`unity_batch_compile.py`）を展開後のパッケージ単体で実行し正常動作を確認した。ホスト側（Claude Code／Codex CLI／Antigravity）での実発火確認は未実施（次回月次監視で実施、上表参照） |

## 更新履歴

| 日付 | 内容 |
|---|---|
| 2026-09-04 | 0.1.0 の本番確認（公開URLからのダウンロード・ハッシュ照合・展開構成確認・scripts/3本の単体実行）を実施し、配布済みバージョン対応表の備考へ記録 |
| 2026-09-04 | 0.1.0 リリース。`.skill` ハッシュを配布済みバージョン対応表に記録 |
| 2026-09-03 | 初版作成。設置先一覧・設置方法を requirements.md 2.3節・12.2節から反映。既知の挙動差なし |
