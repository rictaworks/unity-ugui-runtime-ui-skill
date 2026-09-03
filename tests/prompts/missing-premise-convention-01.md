# テストプロンプト：前提欠落（missing-premise-convention-01）

## 類型

前提欠落（requirements.md 11.1節）— 既存規約あり

## 実行前提（テスト環境）

- Unityプロジェクトが存在する。
- `Assets/Scripts/UI/UiTheme.cs`・`Assets/Scripts/UI/UiFactory.cs`・`Assets/Scripts/UI/UiScreenBase.cs`が既に存在し、色・寸法・生成関数・Build/Renderの骨格が既に定義されている（命名・配置規約が定まっている）。
- 日本語表示に対応するフォントは同梱済み。

## 要求文

```
このプロジェクトには UiFactory.cs や UiTheme.cs など既存のUI共通基盤が
あります。この規約に沿って、新しいランキング画面をuGUIで作成してください。
ScrollRectで順位一覧を表示し、自分の順位だけ強調表示してください。
```
