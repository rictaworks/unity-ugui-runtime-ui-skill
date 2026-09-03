# 期待結果：前提欠落（missing-premise-project-01）

対応プロンプト：`tests/prompts/missing-premise-project-01.md`

## 発火可否

**発火する。** 要求自体はuGUIによる画面新規構築であり対象範囲内（3.2節）。プロジェクトの有無は発火可否ではなく前提収集（F1）の判定事項。

## モード判定（F0）

**構築。**

## 前提収集（F1）の判定

- F1手順1「プロジェクト判定」：`Assets/`・`ProjectSettings/`のいずれも存在しないため「プロジェクト不在」と判定する。
- 出力先を作業ディレクトリ直下の`ugui-output/`に**固定**し、報告に明記する。ファイルの散在を防ぐため、`Assets/Scripts/UI/...`のような推測パスへは書かない。

## 停止可否

**停止しない。** プロジェクト不在は5.2節（F1）の停止条件（手順5：文字体系ゲート）とは異なり、出力先を固定したうえで処理を継続する事項である。

## 期待される報告構造（F6）

7見出しは通常どおり出力される。「前提と既定値」表の「プロジェクト有無」行に「プロジェクト不在（`Assets/`・`ProjectSettings/`とも未検出）。出力先を`ugui-output/`に固定」等が出所「読取」で記載される。「既知の制限」にも同様の注記が入る。

## 生成ファイル名（期待）

すべて作業ディレクトリ直下`ugui-output/`配下に固定される（例）：

- `ugui-output/Scripts/UI/UiTheme.cs`
- `ugui-output/Scripts/UI/UiFactory.cs`
- `ugui-output/Scripts/UI/UiScreenBase.cs`
- `ugui-output/Scripts/UI/Screens/LoginScreen.cs`

`Assets/`配下など、Unityプロジェクトが存在する前提のパスには一切書き込まれないこと。

## 検証観点

- 推測したパス（`Assets/...`等）への書き込みが発生していないこと。
- 出力先固定の事実が報告の「前提と既定値」および「既知の制限」の双方、またはいずれかで明示されていること。
