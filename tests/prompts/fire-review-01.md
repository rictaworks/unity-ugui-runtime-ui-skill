# テストプロンプト：発火・レビュー（fire-review-01）

## 類型

発火・レビュー（requirements.md 11.1節）

## 実行前提（テスト環境）

- Unityプロジェクト内に既存のuGUI画面ビルダー`Assets/Scripts/UI/Screens/SettingsScreen.cs`が存在する。
- このファイルには`EventSystem`生成の欠落、色リテラルの直書き、`Build`と`Render`の責務混在など、重大度の異なる複数の問題が含まれている（レビュー対象として意図的に混在させる）。

## 要求文

```
Assets/Scripts/UI/Screens/SettingsScreen.cs のUIビルダーコードをUXの観点で
レビューしてください。修正はまだしなくていいので、問題点だけ洗い出して
ください。重大度も分かるようにしてください。
```
