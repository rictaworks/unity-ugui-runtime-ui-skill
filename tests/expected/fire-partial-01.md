# 期待結果：発火・部分適用（fire-partial-01）

対応プロンプト：`tests/prompts/fire-partial-01.md`

## 発火可否

**発火する（uGUI部分のみ）。** 要求文は「タイトル画面をuGUIでコードから新規に作る」（対象）と「Editor拡張のInspectorカスタマイズをUI Toolkitで作る」（対象外：UI Toolkit・Editor拡張の双方に該当）の両方を含む。3.4節「部分適用」・F0手順1〜4に従い、uGUI部分にのみ適用される。

## モード判定（F0）

**構築（uGUI部分について）。** 適用部分（タイトル画面）に既存画面への言及・コード評価要求がないため。範囲外部分：「Editor拡張のInspectorカスタマイズ（UI Toolkit）」を保持し、報告の「範囲外の所見」に記載する。

## 停止可否

**停止しない。** 適用部分（タイトル画面のuGUI構築）が空ではないため、F0手順2の「適用部分が空であれば取り下げ」には該当しない。全体を拒否せず、全体を引き受けもしない（3.4節）。

## 期待される報告構造（F6）

7見出しは同一順序。「範囲外の所見」に、Editor拡張・UI ToolkitによるInspectorカスタマイズの要求が本スキルの範囲外である旨が1文で明示され、代替（UI Toolkit・Editor拡張は範囲外）が示される。

## 生成ファイル名（期待）

uGUI部分（タイトル画面）のみが生成される。UI Toolkit・Editor拡張に関するファイル（UXML・USS・Editor拡張C#等）は一切生成されない。

- `Assets/Scripts/UI/UiTheme.cs`（新規、共通基盤未検出のため）
- `Assets/Scripts/UI/UiFactory.cs`（新規）
- `Assets/Scripts/UI/UiScreenBase.cs`（新規）
- `Assets/Scripts/UI/Screens/TitleScreen.cs`（新規）

## 検証観点

- UI Toolkit・Editor拡張に関する記述やコードが成果物に一切含まれないこと（`UnityEditor`名前空間・`OnGUI`・`AssetDatabase`を含めない不変条件1とも整合）。
- 「範囲外の所見」が「該当なし」ではなく、具体的な範囲外要求を名指しして記載されていること。
