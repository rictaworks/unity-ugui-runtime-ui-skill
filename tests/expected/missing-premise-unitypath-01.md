# 期待結果：前提欠落（missing-premise-unitypath-01）

対応プロンプト：`tests/prompts/missing-premise-unitypath-01.md`

## 発火可否

**発火する。** カート画面の新規uGUI構築要求であり、複数状態（空表示を含む）を扱うため対象範囲内（3.2節）。

## モード判定（F0）

**構築。**

## 前提収集（F1）の判定

- F1手順7「検証段階の決定」：`UNITY_PATH`が未設定（または実行不可）のため、検証段階は**静的検査段階**に切り替わる（CLI段階にはならない）。

## 停止可否

**停止しない。** 検証段階の切り替えは停止条件ではなく、F5（検証）の実施範囲を狭める事項である。

## 検証（F5）への反映

- 実施：`scripts/lint_ugui_csharp.py`（禁止パターン・必須構成の検査）、`scripts/check_contrast.py`（コントラスト検査）。
- **未実施**：`scripts/unity_batch_compile.py`によるCLIコンパイル確認、`UiResolutionSweepTests`による解像度スイープ（いずれも`UNITY_PATH`が必要なCLI段階の検証）。
- 未実施の検証を実施済みとして報告しない（不変条件12）。

## 期待される報告構造（F6）

7見出しは通常どおり。「検証段階と結果」表で以下のように記載される：

| 段階 | 実施 | 結果 |
|---|---|---|
| 静的検査（lint_ugui_csharp.py） | 実施 | 禁止パターンなし 等 |
| コントラスト検査（check_contrast.py） | 実施 | 全組み合わせが4.5以上 等 |
| CLIコンパイル（unity_batch_compile.py） | 未実施（`UNITY_PATH`未設定） | — |
| 解像度スイープ（UiResolutionSweepTests） | 未実施（CLI段階のみ） | — |

「既知の制限」にも「`UNITY_PATH`が未設定のためCLIコンパイル・解像度スイープは未実施。静的検査のみで報告している」旨が明記される。

## 生成ファイル名（期待）

- `Assets/Scripts/UI/UiTheme.cs`・`UiFactory.cs`・`UiScreenBase.cs`（未検出のため新規）
- `Assets/Scripts/UI/Screens/CartScreen.cs`（新規）
- `Assets/Tests/PlayMode/UiResolutionSweepTests.cs`・`Assets/Editor/UiBatchCompileCheck.cs`（コード自体は生成されるが、実行はされない）

## 検証観点

- CLIコンパイル・解像度スイープが「実施」「合格」等として誤って報告されていないこと（不変条件12）。
- 静的検査（lint・contrast）は`UNITY_PATH`の有無に関わらず必ず実施されること（5.6節手順1「全段階共通」）。
