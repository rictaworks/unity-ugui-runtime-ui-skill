# 期待結果：参照未読（reference-unread-01）

対応プロンプト：`tests/prompts/reference-unread-01.md`

## 発火可否

**発火する。** HUD画面の新規uGUI構築要求であり、ScrollRect・解像度追従を含み対象範囲内（3.2節）。本来であれば「参照ファイルの読み込み条件」表（`SKILL.md`末尾）により`references/layout.md`・`references/components.md`が読み込み対象になるが、本テストでは意図的に読み込ませない。

## モード判定（F0）

**構築。**

## 停止可否

**停止しない。**

## 検証の主眼

`references`を読まずに`SKILL.md`のみで実行された場合でも、以下の不変条件（`SKILL.md`「設計原則（不変条件）」12項目・requirements.md 6章）を満たす成果物が生成されることを確認する。`references/*`の詳細な落とし穴解説を欠いても、本文常設の12項目だけで最低限の正しさが担保される設計になっているかを検証する。

| # | 不変条件 | 本テストでの具体的な確認点 |
|---|---|---|
| 1 | `UnityEditor`名前空間・`OnGUI`・`AssetDatabase`を実行時コードに含めない | 生成された`HudScreen.cs`等に該当パターンがないこと |
| 2 | `EventSystem`と入力モジュールを1つ用意する | シーンに無ければ生成するコードが含まれること |
| 3 | 各Canvasに`CanvasScaler`（`ScaleWithScreenSize`）と`GraphicRaycaster`を付与する | 生成コードで両者が設定されること |
| 4 | LayoutGroupの子に`ContentSizeFitter`を付与しない | ステータス一覧の各行（LayoutGroupの子）に`ContentSizeFitter`が付与されていないこと |
| 5 | ScrollRectはViewport（`RectMask2D`）とContent（LayoutGroup＋`ContentSizeFitter`）で組む | 横スクロールのステータス一覧がこの構成になっていること（`HorizontalLayoutGroup`＋`ContentSizeFitter`をContent側に付与） |
| 6 | 生成した要素の参照はフィールドで保持し、名前検索で取り直さない | `GameObject.Find`・`transform.Find`が生成コードに現れないこと |
| 9 | 色・寸法・文字サイズ・文言はテーマまたは定数に集約する | `UiTheme`（新規または既存）にステータス表示の色・寸法が集約されること |
| 10 | タップ領域44px以上・コントラスト比4.5以上・状態は色以外でも区別する | HUD上の操作可能要素（あれば）がこの基準を満たすこと |

## 期待される報告構造（F6）

7見出しは通常どおり出力される（参照未読であっても`SKILL.md`本文のみで報告構造自体は完結する）。

## 生成ファイル名（期待）

- `Assets/Scripts/UI/UiTheme.cs`・`UiFactory.cs`・`UiScreenBase.cs`（未検出のため新規）
- `Assets/Scripts/UI/Screens/HudScreen.cs`（新規）

## 検証観点

- `references/layout.md`・`references/components.md`が持つ詳細手順（落とし穴回避の具体例等）を欠いても、`SKILL.md`本文の不変条件12項目が守られていること。
- 参照未読によって不変条件違反（特に不変条件4・5・6・9）が発生した場合は、`SKILL.md`本文への不変条件の常設（設計原則、CLAUDE.md「不変条件（設計原則）」節）が不十分であることを示す欠陥として扱う。
