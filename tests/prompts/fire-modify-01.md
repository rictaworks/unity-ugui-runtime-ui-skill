# テストプロンプト：発火・改修（fire-modify-01）

## 類型

発火・改修（requirements.md 11.1節）

## 実行前提（テスト環境）

- Unityプロジェクト内に、既存のuGUI画面ビルダー`Assets/Scripts/UI/Screens/ShopScreen.cs`が存在する。
- `ShopScreen.cs`は縦持ち（アスペクト比が縦長）で購入ボタンが画面外にはみ出し、タップ領域が不足している。
- 同ディレクトリの他画面（例：`InventoryScreen.cs`）には要求と無関係な不変条件違反（`GameObject.Find`による再取得など）が別途存在する。

## 要求文

```
既存の ShopScreen.cs のuGUI実装で、スマートフォンの縦持ちだとボタンが
画面外にはみ出して押せません。購入ボタンの押しづらさとレイアウト崩れ
だけを直してください。他の画面や機能には触れないでください。
```
