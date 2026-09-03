# 期待結果：発火・構築（fire-build-01）

対応プロンプト：`tests/prompts/fire-build-01.md`

## 発火可否

**発火する。**

- `description`（`SKILL.md`冒頭）の発火語「Unity」「uGUI」「Canvas」「ScrollRect」「レスポンシブ」「WebGL」のうち複数（Unity・uGUI・ScrollRect・WebGL・レイアウト崩れ対応）を含む。
- 単一手順では完了しない要求（新規画面構築＋複数状態設計＋解像度追従）であり、3.2節「発火すべき要求の類型」の「画面・パネル・HUD・メニューをuGUIでコードから新規に作る」「ScrollRectによる一覧、状態表示（読込中・空・エラー）…など複数コンポーネントの組み合わせを実装する」「解像度・アスペクト比の変化に追従させる」の3つに該当する。

## モード判定（F0）

**構築。** 既存画面への言及がなく、コード評価の要求でもないため。範囲外部分はなし。

## 前提収集（F1）の判定

| 項目 | 期待される判定 | 出所 |
|---|---|---|
| プロジェクト有無 | `Assets/`・`ProjectSettings/`とも存在するためUnityプロジェクトと判定 | 読取 |
| 既存UI規約 | 未検出。共通基盤を新規に起こす対象になる | 読取 |
| 文字体系 | 日本語（CJK）を含む | 読取（要求文） |
| 文字体系ゲート | `Assets/Resources/Fonts/`にCJK対応フォントが存在するため**停止しない** | 読取 |
| テキスト方式 | 既存コードが`TMPro`を使用していないため`UnityEngine.UI.Text`を用いる | 読取 |
| 参照解像度・入力方式 | 既定値（1920×1080、マウス＋タッチ） | 既定 |
| 検証段階 | `UNITY_PATH`未設定のため静的検査段階 | 読取 |

## 停止可否

**停止しない。** 文字体系ゲート（不変条件7・F1手順5）に該当するCJK文言があるが、対応フォントが同梱されているため先へ進む。

## 期待される報告構造（F6）

以下7見出しがこの順序で出力される（`assets/report-template.md`と同一）：

1. 対象と模式図
2. 前提と既定値
3. UX判断
4. 生成・変更ファイル
5. 検証段階と結果
6. 既知の制限
7. 範囲外の所見（該当なしと明記される）

## 生成ファイル名（期待）

共通基盤が未検出のため新規に起こされる：

- `Assets/Scripts/UI/UiTheme.cs`（新規）
- `Assets/Scripts/UI/UiFactory.cs`（新規）
- `Assets/Scripts/UI/UiScreenBase.cs`（新規）
- `Assets/Scripts/UI/Screens/InventoryScreen.cs`（新規。画面名は要求内容から妥当に命名されていればよく、厳密一致は求めない）
- `Assets/Tests/PlayMode/UiResolutionSweepTests.cs`
- `Assets/Editor/UiBatchCompileCheck.cs`

## 検証観点（不変条件との対応）

- 不変条件2：`EventSystem`が無ければ生成される。
- 不変条件3：Canvasに`CanvasScaler`（`ScaleWithScreenSize`）と`GraphicRaycaster`が付与される。
- 不変条件5：ScrollRectがViewport（`RectMask2D`）／Content（`VerticalLayoutGroup`＋`ContentSizeFitter`）の構成で組まれる。
- 不変条件4：LayoutGroupの子に`ContentSizeFitter`が付与されない。
- 不変条件6：生成した要素の参照はフィールド保持され、`GameObject.Find`・`transform.Find`で取り直されない。
- 不変条件9・10：色・寸法・文字サイズ・文言が`UiTheme`に集約され、タップ領域44px以上・コントラスト比4.5以上を満たす。
- 検証段階と結果に「CLIコンパイル：未実施（`UNITY_PATH`未設定）」「解像度スイープ：未実施（CLI段階のみ）」が明記され、実施済みとして報告されない（不変条件12）。

## 参照ファイル読み込み（期待）

ScrollRectを含むため`references/layout.md`・`references/components.md`が、CJK文字を扱うため`references/text-and-fonts.md`が読み込まれる。`references/ux-checklist.md`の読み込み条件は「構築モードで画面を2つ以上扱うとき、レビューモードの常時」であり、本要求は在庫確認画面という単一画面の複数状態（読込中・空・エラー）を扱うものであって画面数は1つのため、この条件には該当せず読み込まれない。
