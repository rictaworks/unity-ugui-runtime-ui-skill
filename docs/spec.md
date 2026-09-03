# docs/spec.md — 本書

この文書は `requirements.md`（設計書・仕様のSingle Source of Truth）の写しを起点とする要約版です。`requirements.md` 7.1節のリソース構成表で `docs/spec.md # 本書` として定義されている位置づけに対応します。

**正はあくまで `requirements.md` です。** この文書と `requirements.md` の内容が食い違う場合は `requirements.md` が優先し、この文書側を修正してください。判断に迷ったときや詳細な手順・判断基準が必要なときは、要約に頼らず必ず `requirements.md` の該当節を直接参照してください。

参照元：[`requirements.md`](../requirements.md)（参照日 2026年9月2日時点の内容に基づく。1.5節参照）

---

## 1. スキルの目的と対象範囲

Unity（WebGL）のuGUIによるユーザーインターフェースを、Editor GUI操作なし・C#コードのみで新規構築・改修・レビューする際に、UX設計判断とuGUI実装の手順・判断基準をエージェントに与える（`requirements.md` 2.1節）。

対象範囲は `requirements.md` 2.2節に固定されている。UI Toolkit（UXML/USS/VisualElement）・Editor拡張（EditorWindow・IMGUI `OnGUI`・Inspector拡張）・TextMeshProのフォントアセット生成・シェーダー/VFX・Unity以外のUIは明示的に対象外。判断に迷った場合は範囲を独自に広げず `requirements.md` 2.2節に立ち返る。

## 2. 対象バージョン（1.5節）

対象ホスト・Agent Skills標準・Unityのバージョンは `requirements.md` 1.5節の表に固定されている。この表は改訂のたびに一次情報で再確認し、参照日を更新する運用（13章）になっているため、この文書には数値を転記せず `requirements.md` 1.5節を都度参照すること。

## 3. 対象ホストと設置先（2.3節）

対象ホストはClaude Code・Codex CLI・Antigravityの3種。ワークスペース設置先・グローバル設置先・明示呼び出し方法の一覧は `requirements.md` 2.3節の表が正。設置先パスは参照日時点の一次情報・コミュニティ検証に基づくため、改訂フロー（13章）で定期的に再確認される。個別ホストでの実際の設置状況・挙動差は [`docs/hosts.md`](./hosts.md) に記録する。

## 4. 手順の論理構造（5章）

`SKILL.md` はF0〜F7の手順で構成される。

| 手順 | 内容 |
|---|---|
| F0 | 適用範囲確認（confirmScope）。対象範囲外の要求を切り分け、部分適用を判断する |
| F1 | 前提収集（collectPremises） |
| F2 | UX設計（designUx） |
| F3 | コード構造設計（designStructure） |
| F4 | 実装生成（generateCode） |
| F5 | 検証（verify） |
| F6 | 報告（report） |
| F7 | レビューモード固有手順（reviewExisting） |

詳細は `requirements.md` 5章を参照。

## 5. 設計原則（不変条件、6章）

`references` を読まずに `SKILL.md` のみで実行された場合でも誤った成果物が生成されないよう、12項目の不変条件が `requirements.md` 6章に定義され、`SKILL.md` 本文に常設されている（参照ファイルへ逃がさない）。代表的な不変条件の例：

- `UnityEditor` 名前空間・`OnGUI`・`AssetDatabase` を実行時コードに含めない
- 生成した要素の参照はフィールドで保持し、`GameObject.Find`・`transform.Find` で取り直さない
- 色・寸法・文字サイズ・文言は `UiTheme` または定数に集約する

全12項目は `requirements.md` 6章を参照。

## 6. リソース構成（7.1節）

配布単位は `skills/unity-ugui-runtime-ui/`（Single Source of Truth）で、`SKILL.md`・`references/`（6ファイル）・`scripts/`（3ファイル）・`assets/`（6点）から成る。`tests/{prompts,expected}`・`docs/{spec.md,hosts.md,CHANGELOG.md}` を含むリポジトリ全体の構成は `requirements.md` 7.1節の構成図が正。この構成にないディレクトリを先回りして作らない。

## 7. 検証要件（11章）

- `tests/prompts/` に発火・構築、発火・改修、発火・レビュー、発火・部分適用、非発火、前提欠落、参照未読の7類型を揃え、期待結果を `tests/expected/` に置く（11.1節）。
- 同一プロンプトをClaude Code・Codex・Antigravityの3ホストで実行し、発火可否・停止可否・報告の見出し構造・生成ファイル名の一致を確認する（11.2節）。差異は [`docs/hosts.md`](./hosts.md) に記録する。
- CIで自動化する検査・Windows環境で実行するUnity CLI検査・人間が手動で行う工程の切り分けは `requirements.md` 11.3〜11.5節を参照。

## 8. 配布と設置（12章）

- 配信先はGitリポジトリとし、`skills/unity-ugui-runtime-ui/` をSingle Source of Truthとする。パッケージは `.skill` 形式でCIが生成し、リリースに添付する（12.1節）。
- 各ホストへの設置はsymlinkで行う。ホストごとの設置方法は `requirements.md` 12.2節の表が正。実際の設置状況は [`docs/hosts.md`](./hosts.md) に記録する。
- 本スキルは外部APIを呼ばない。唯一の環境依存値は環境変数 `UNITY_PATH`（Unity実行パス）で、値を成果物・内部文書に記載しない（12.3節）。

## 9. 保守と監視（13章・14章）

- バージョンは `metadata.version`（セマンティックバージョン）。粒度は13.1節：`description` の変更・手順の分岐追加はマイナー、不変条件の追加・出力構造の変更はメジャー、文言修正はパッチ。変更履歴は [`docs/CHANGELOG.md`](./CHANGELOG.md) に記す。
- 改訂フロー（13.3節）・月次監視の体制（14章）の詳細は `requirements.md` を参照。この文書自体の改訂もこのフローに従う。

---

## この文書の更新方針

- `requirements.md` の該当節が改訂されたら、この文書も同じPR内、または追随するPRで更新する。
- この文書は要約であり、`requirements.md` の内容を置き換えない。数値（バージョン・行数上限など）が変動しやすい節は、値を転記せず参照する形にとどめる。
