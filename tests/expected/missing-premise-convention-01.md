# 期待結果：前提欠落（missing-premise-convention-01）

対応プロンプト：`tests/prompts/missing-premise-convention-01.md`

## 発火可否

**発火する。** ScrollRectを含む一覧画面の新規uGUI構築要求であり対象範囲内（3.2節）。

## モード判定（F0）

**構築。**

## 前提収集（F1）の判定

- F1手順3「既存規約探索」：`UiTheme.cs`・`UiFactory.cs`・`UiScreenBase.cs`を検出し、命名・配置規約が既に定まっていると判定する。**見つかった規約は新規作成より優先する。**
- 文字体系・フォント同梱は問題ないため、文字体系ゲート（手順5）には該当しない。

## 停止可否

**停止しない。**

## コード構造設計（F3）への反映

- F3手順1「共通基盤の有無」の判定で「既に存在する」となり、`UiTheme`・`UiFactory`・`UiScreenBase`を**新規に起こさない**。
- 新規画面クラス（例：`RankingScreen.cs`）のみを既存規約の命名・配置に合わせて追加する。

## 期待される報告構造（F6）

7見出しは通常どおり。「前提と既定値」表の「既存UI規約」行に「`UiFactory.cs`等を検出。命名・配置はこれに従う」が出所「読取」で記載される。「生成・変更ファイル」欄では`UiTheme.cs`・`UiFactory.cs`・`UiScreenBase.cs`が「変更なし（既存流用）」として一覧に含まれる。

## 生成ファイル名（期待）

- `Assets/Scripts/UI/Screens/RankingScreen.cs`（新規。既存の命名・配置規約に従う）

`UiTheme.cs`・`UiFactory.cs`・`UiScreenBase.cs`は新規作成されない（既存を流用）。

## 検証観点

- 既存の命名・配置規約と異なる独自の共通基盤が新規に作られていないこと。
- 色・寸法・文字サイズは既存`UiTheme`の値のみを用い、新たなリテラルを追加していないこと（不変条件9）。
