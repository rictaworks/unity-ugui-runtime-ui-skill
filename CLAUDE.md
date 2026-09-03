# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 安全ルール（最優先）

### 削除系コマンドの禁止（重要）

以下のルールはこのワークスペース内のすべての会話で絶対に守られる：

- Claude はファイルまたはディレクトリを削除するコマンドを一切生成してはならない。
  例：rm, rm -rf, rm *, rmdir, unlink, cache --delete,
      lftp mirror --delete, rsync --delete, git clean -df, find -delete 等。

- 削除が必要な場合でも、Claude は削除コマンドを提案せず、
  「手動で削除してください」といった説明に留めること。

- 削除の推奨・削除操作の自動判断も禁止。

- ssh / lftp / デプロイ系スクリプトを生成する場合でも、
  削除コマンドの生成は禁止。

これらはすべての会話・コード生成に適用される。

### シークレット管理（重要）

- `config/master.key` など機密ファイルを `git add` するコードを生成してはならない
- デプロイスクリプト・セットアップ手順でも同様
- シークレットは必ず環境変数（`RAILS_MASTER_KEY` 等）で渡すこと
- `.gitignore` への追加を確認する手順を必ずコードに含めること
- 初回コミット前に `git status` でステージング確認を促すこと
- 本スキルは外部APIを呼ばない。唯一の環境依存値は `UNITY_PATH`（Unity実行パス）で、値を成果物・内部文書に書かない（12.3節）

---

## プロジェクト概要

Unity（WebGL）の uGUI 画面を、Editor GUI 操作なし・C# コードのみで新規構築・改修・レビューする際の UX 設計判断と uGUI 実装の手順・判断基準を与える **Agent Skill** を作るリポジトリ。Web アプリケーションでもライブラリでもない。

| 項目 | 値 |
|---|---|
| スキル名 | `unity-ugui-runtime-ui` |
| 対象エディション | 製品版フルエディション（`SKILL.md` + `references` + `scripts` + `assets` の全構成） |
| 対象ツール | Claude Code・Codex CLI・Antigravity（同一 `SKILL.md` で発火） |
| 配布方式 | Git リポジトリ。パッケージは `.skill` 形式で CI が生成しリリースに添付 |

- 仕様の Single Source of Truth は `requirements.md`。判断は必ずここを読んでから行い、推測で補完しない。
- リポジトリ本体（`skills/unity-ugui-runtime-ui/`）を Single Source of Truth とし、各ツールのスキルディレクトリへは symlink で設置する（12.2節）。
- 2026-09-03 時点では設計書（`requirements.md`）のみで、`skills/`・`tests/`・`docs/` は未着手。

## 開発の正

WSL2（`~/github/rictaworks/unity-ugui-runtime-ui-skill`）。Windows側にクローンは持たない。ただし Unity CLI 検証（`scripts/unity_batch_compile.py`）は `UNITY_PATH` を設定した **Windows環境**で実行する（11.4節）——検証段階だけ実行環境が異なる点に注意する。

## 前提

- 時刻はすべて JST。日時を書くときはタイムゾーンを明示する。
- ファイルのエンコードはすべて UTF-8（BOMなし）、改行は LF。
- 内部文書・コメント・PR本文は日本語。コード識別子と技術用語は原語のまま。
- 対象範囲・対象外は `requirements.md` 2.2節に固定されている。UI Toolkit・Editor拡張・IMGUI・TMPフォント生成は明示的に対象外。判断に迷ったら範囲を広げず `requirements.md` に立ち返る。

## 開発フロー（TDD厳守）

`plan` → `red test` → `coding` → `green test` の順を厳守する。

- `scripts/` の Python 検査（`lint_ugui_csharp.py`・`check_contrast.py`・`unity_batch_compile.py`）は単体テストを先に書く。追加パッケージを要求せず標準ライブラリのみで動作させる（15章）。
- `SKILL.md` の手順自体は `tests/prompts/`（発火・非発火・前提欠落・参照未読の各類型）と `tests/expected/`（期待結果）の対応で検証する（11.1節）。通常のユニットテストではなくプロンプト対応表であることに注意する。
- 同一プロンプトを Claude Code・Codex・Antigravity の3ホストで実行し、発火可否・停止可否・報告の見出し構造・生成ファイル名の一致を確認する（11.2節）。差異は `docs/hosts.md` に記録する。

## 不変条件（設計原則）

`references` を読まずに `SKILL.md` のみで実行された場合でも誤った成果物が生成されないよう、`requirements.md` 6章に12項目の不変条件がある。**`SKILL.md` を執筆する際はこの12項目を本文に常設し、参照ファイルへは逃がさない。**

## リソース構成（`requirements.md` 7.1節が正）

```
skills/unity-ugui-runtime-ui/   # 配布単位（Single Source of Truth）
├── SKILL.md                    # 250〜300行目標・上限500行（7.2節）
├── references/                 # 6ファイル・条件時読み込み（7.3節の表に従う）
├── scripts/                    # lint_ugui_csharp.py / check_contrast.py / unity_batch_compile.py
└── assets/                     # UiTheme.cs.tmpl 等テンプレート6点
tests/{prompts,expected}/
docs/{spec.md,hosts.md,CHANGELOG.md}
```

構成にないディレクトリ（`TASKS/`・`DEBUG/`・`app-ui/` 等）を先回りして作らない。7.1節に無いものが必要になったら、まず `requirements.md` の改訂を検討する。

## 配布と設置

- Agent Plugins形式は採用しない（12.1節に理由：MCPサーバーを伴わず`.skill`形式に対して利点がない）。
- 設置はホストごとに `.claude/skills/`・`.agents/skills/` へのsymlinkで行う（12.2節）。CodexとAntigravityは同じ `.agents/skills` を読むため、ワークスペースでは `.agents/skills` をディレクトリ単位でsymlinkする方式に統一する。

## ブランチ運用・PR・CI

- mainブランチでの直接作業を禁止する。変更前に必ずブランチを切る。
- コミット前に `/security-review`（`.claude/OWASP10.md` の観点）を実行する。
- マージ前に `reviewer`・`pr-checker` agent を実行するフックを用意する。
- CI（`.github/workflows/ci.yml`）は `skills-ref validate` によるフロントマター・命名検証、`SKILL.md` の行数上限（500）と参照ファイルの目次有無、参照ファイルへの相対リンク確認、禁止内容検査（資格情報・メールアドレス・個人名・ホスト固有フロントマターフィールド）、`scripts/` の単体テスト、`.skill` パッケージ生成を行う（11.3節）。

## コーディング規約

- **フォールバック禁止。** 値が取得できない・処理が失敗した場合に既定値で握りつぶさない。
- **グローバル変数を禁止する。**
- 色・寸法・文字サイズ・文言は `UiTheme` または定数に集約する（不変条件9）。C# テンプレート自体にもこの規約を適用する。
- `UnityEditor` 名前空間・`OnGUI`・`AssetDatabase` を実行時コードに含めない（不変条件1）。
- 生成した要素の参照はフィールドで保持し、`GameObject.Find`・`transform.Find` で取り直さない（不変条件6）。

## 監視・保守

- 月次、および対象ホストのリリース後に `tests/prompts/` を3ホストで再実行し、発火可否・停止可否・出力構造の一致を確認する（14章）。結果は `tests/results/<日付>/` に記録する。
- バージョンはセマンティックバージョン（`metadata.version`）。GitHub Releasesのタグは `メジャー2桁.マイナー2桁.デバッグ2桁`（例：`01.01.00`）、注釈付きタグ（`git tag -a`）とする。
- 対象ホスト・Agent Skills標準・Unityのバージョンは `requirements.md` 1.5節に固定。改訂のたびに一次情報で再確認し参照日を更新する（13章）。

## 参照ドキュメント

| ファイル | 内容 |
|---|---|
| `requirements.md` | 本スキルの仕様（SSOT） |
| `.claude/QC10.md` | 品質管理10項目 |
| `.claude/OWASP10.md` | OWASP Top 10（security review観点） |
| `.claude/CC.md` | コンプライアンスチェック10項目 |
| `.claude/Manager.md` | GitHub Issueベース並列開発の運用 |
| `DOCS/TM.md` | テストメソッドとテストフレームワーク |
| `DOCS/DP.md` | 開発原則（development-principles） |
| `DOCS/CRAP.md` | デザイン4原則 |

## agent構成

`.claude/agents/` に定義する。規模に応じて使い分ける。

| agent | 役割 |
|---|---|
| `director` | 目的と優先順位の決定、範囲外の切り分け（F0適用範囲確認・部分適用の判断。5.1節） |
| `project-manager` | Issue分割・依存設計・進行管理（`.claude/Manager.md` に準拠） |
| `unity-ux-designer` | UX設計判断（情報階層・レイアウト方式・状態・フィードバック・導線・追従規則・アクセシビリティ判定。F2/5.3節） |
| `debugger` | Unity CLIコンパイルエラー・解像度スイープ検出結果の原因特定（5.6節） |
| `tester` | `tests/prompts/` と `tests/expected/` の対応表作成、`scripts/` 単体テストの作成・実行 |
| `pr-checker` | PRタイトル・本文の日本語整形。**レビューは行わない** |
| `reviewer` | `references/review-rubric.md` の観点でのコードレビュー、`.claude/{CC,OWASP10,QC10}.md`・`DOCS/{CRAP,DP,TM}.md` の充足確認 |
| `deployer` | 各ホストへのsymlink設置と設置先の実機確認（12.2節） |
| `service-manager` | 月次監視（14章）・改訂フロー（13.3節）の運用確認 |
