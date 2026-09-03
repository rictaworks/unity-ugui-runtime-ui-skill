# unity-ugui-runtime-ui-skill

Unity（WebGL）の uGUI 画面を、Editor GUI 操作なし・C# コードのみで新規構築・改修・レビューする際に、UX 設計判断と uGUI 実装の手順・判断基準をエージェントに与える **Agent Skill**（`unity-ugui-runtime-ui`）を配布するリポジトリです。

このリポジトリ自体は Web アプリケーションでもライブラリでもなく、Claude Code・Codex CLI・Antigravity 向けの Agent Skill の設計書・実装・検証資材一式です。仕様の Single Source of Truth（正）は [`requirements.md`](./requirements.md) です。判断に迷った場合は本 README ではなく `requirements.md` を参照してください。

## スキル概要

| 項目 | 値 |
|---|---|
| スキル名 | `unity-ugui-runtime-ui` |
| 対象エディション | 製品版フルエディション（`SKILL.md` + `references` + `scripts` + `assets` の全構成） |
| 対象ツール | Claude Code・Codex CLI・Antigravity（同一 `SKILL.md` で発火） |
| 配布方式 | Git リポジトリ。パッケージは `.skill` 形式で CI が生成しリリースに添付 |

## 対象範囲

`requirements.md` 2.2節が正。要約すると以下のとおりです。

- **対象**：Canvas / CanvasScaler / RectTransform（アンカー・ピボット）/ LayoutGroup系 / ContentSizeFitter / LayoutElement / Image / RawImage / Text（`UnityEngine.UI.Text`）/ Button / Toggle / Slider / Scrollbar / ScrollRect / Dropdown / InputField / Mask / RectMask2D / EventSystem / Selectable のナビゲーション / Graphic Raycaster
- **対象**：UX設計（情報階層、画面構成、レイアウト方式の選択、状態、フィードバック、操作導線、解像度・アスペクト比追従、アクセシビリティ基礎）
- **対象**：検証（Unity CLI batchmode によるコンパイル確認、Play Modeテストによる解像度スイープ、生成コードの静的検査）
- **対象外**：UI Toolkit（UXML・USS・VisualElement）、Editor拡張（EditorWindow・IMGUI `OnGUI`・Inspector拡張）、TextMeshProのフォントアセット生成、シェーダー・VFX、Unity以外のUI、ゲームロジック単体

対象範囲外の判断が必要な場合は、範囲を独自に広げず `requirements.md` に立ち返ってください。

## 対応ホストと設置先

`requirements.md` 2.3節が正。

| ホスト | ワークスペース設置先 | グローバル設置先 | 明示呼び出し |
|---|---|---|---|
| Claude Code | `.claude/skills/<name>/` | `~/.claude/skills/<name>/` | `/unity-ugui-runtime-ui` |
| Codex CLI | `.agents/skills/<name>/` | `~/.agents/skills/<name>/` | `$unity-ugui-runtime-ui` |
| Antigravity | `.agents/skills/<name>/`（`.agent/skills/`も後方互換） | `~/.gemini/antigravity/skills/<name>/` | 会話中でスキル名に言及 |

`<name>` は `unity-ugui-runtime-ui` です。リポジトリ本体（`skills/unity-ugui-runtime-ui/`）を Single Source of Truth とし、各ホストのスキルディレクトリへは symlink で設置します（`requirements.md` 12.2節）。設置先パスは参照日時点の一次情報・コミュニティ検証に基づくため、改訂フロー（`requirements.md` 13章）で定期的に再確認されます。

## 開発フロー

開発ルール（安全ルール・開発の正・開発フロー・不変条件・リソース構成・ブランチ運用・コーディング規約・agent構成など）の詳細は [`CLAUDE.md`](./CLAUDE.md) を参照してください。開発は `plan` → `red test` → `coding` → `green test` の TDD 手順を厳守します。

## 関連ドキュメント

| ファイル | 内容 |
|---|---|
| [`requirements.md`](./requirements.md) | 本スキルの仕様（SSOT） |
| [`CLAUDE.md`](./CLAUDE.md) | 開発ルール・agent構成 |
| [`DOCS/TM.md`](./DOCS/TM.md) | テストメソッドとテストフレームワーク |
| [`DOCS/DP.md`](./DOCS/DP.md) | 開発原則（development-principles） |
| [`DOCS/CRAP.md`](./DOCS/CRAP.md) | デザイン4原則 |
