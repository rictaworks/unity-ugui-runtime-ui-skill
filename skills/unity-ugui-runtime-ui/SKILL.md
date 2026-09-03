---
name: unity-ugui-runtime-ui
description: >-
  Unity（WebGL）のuGUI画面をEditor GUI操作なし・C#コードのみで新規構築・改修・レビューする際に使う。
  Canvas・CanvasScaler・RectTransform・LayoutGroup・ScrollRect・Buttonなどの実装と、情報階層・レイアウト方式・状態・フィードバック・導線・解像度追従・アクセシビリティといったUX設計判断を扱う。
  Unity・uGUI・Canvas・RectTransform・ScrollRect・Button・レイアウト・レスポンシブ・使いやすさ・WebGLのいずれかに言及し、複数手順を要する要求で発火する。
  UI Toolkit（UXML/USS）、EditorWindow・IMGUI、TextMeshProのフォントアセット生成、Unity以外のUIには使わない。
license: See LICENSE
metadata:
  version: 0.1.0
---

# unity-ugui-runtime-ui

## 目的

Unity（WebGL）のuGUIによるユーザーインターフェースを、Editor GUI操作なし・C#コードのみで新規構築・改修・レビューする際に、UX設計判断とuGUI実装の手順・判断基準を与える。

## 対象範囲

| 区分 | 内容 |
|---|---|
| 対象 | Canvas / CanvasScaler / RectTransform（アンカー・ピボット）/ LayoutGroup系 / ContentSizeFitter / LayoutElement / Image / RawImage / Text（`UnityEngine.UI.Text`）/ Button / Toggle / Slider / Scrollbar / ScrollRect / Dropdown / InputField / Mask / RectMask2D / EventSystem / Selectable のナビゲーション / Graphic Raycaster |
| 対象 | UX設計：情報階層、画面構成、レイアウト方式の選択、状態（初期・読込中・空・エラー・無効）、フィードバック（押下遷移・トースト・確認）、操作導線（戻る・フォーカス順・キーボード操作）、解像度・アスペクト比追従、アクセシビリティ基礎（タップ領域・コントラスト・色以外の区別・最小文字サイズ） |
| 対象 | 検証：Unity CLI（batchmode）によるコンパイル確認、Play Modeテストによる解像度スイープ、生成コードの静的検査 |
| 対象外 | UI Toolkit（UXML・USS・VisualElement）、Editor拡張（EditorWindow・IMGUI `OnGUI`・Inspector拡張）、TextMeshProのフォントアセット生成、シェーダー・VFX、Unity以外のUI（Web・ネイティブ・他エンジン）、ゲームロジック単体 |

要求が上記の対象と対象外の双方を含む場合、対象外部分は「本スキルの範囲外」と明示したうえで通常処理に委ねる。全体を拒否せず、全体を引き受けもしない。

## 手順

以降の各手順は、受け取るもの・判定すること・返すものを持つ。前の手順の出力が次の手順の入力になる。

### F0：適用範囲確認

**入力**：要求文。

**出力**：モード（構築／改修／レビュー）、適用部分、範囲外部分。

**手順**

1. 要求文を「uGUIでコードから作る・直す・見る」に該当する部分と、上記「対象範囲」の対象外に該当する部分に分ける。
2. 適用部分が空であれば、スキルの適用を取り下げる。範囲外である旨と代替（UI Toolkit・Editor拡張・TMPフォント生成は本スキルの範囲外）を1文で示して終了する。
3. 適用部分について、既存画面への言及があれば改修、コード評価の要求であればレビュー、それ以外を構築とする。複数に該当する場合はレビュー→改修→構築の順に優先する（既存物の把握を先行させる）。
4. 範囲外部分があれば、最終報告の「範囲外の所見」に記載する対象として保持する。

### F1：前提収集

**入力**：作業ディレクトリ、要求文。

**出力**：前提セット（プロジェクト有無、Unityバージョン、既存規約、文字体系、テキスト方式、参照解像度、入力方式、検証段階）と、前提ごとの出所（読取／既定／利用者指定）。

**手順**

1. **プロジェクト判定**：`Assets/`と`ProjectSettings/`の双方が存在すればUnityプロジェクトとする。いずれかが無ければ「プロジェクト不在」とし、出力先を作業ディレクトリ直下の`ugui-output/`に固定して報告に明記する。ファイルの散在を防ぐため、推測したパスへは書かない。
2. **バージョン**：`ProjectSettings/ProjectVersion.txt`を読む。6000.0未満は`LegacyRuntime.ttf`の名称差など互換注意点を報告に付す。
3. **既存規約探索**：`Assets/`配下のC#から、`UnityEngine.UI`を参照するクラス、`Theme`・`Palette`・`UiFactory`・`Screen`等の命名、`TMPro`名前空間の使用、`Resources/`配下のフォントファイル（`.ttf`・`.otf`）とTMPフォントアセットを列挙する。見つかった規約（配置・命名・テーマ）は新規作成より優先する。
4. **テキスト方式**：既存コードが`TMPro`を使用し、かつ表示対象の文字体系をカバーするTMPフォントアセットが既に存在する場合のみTextMeshProを用いる。それ以外は`UnityEngine.UI.Text`を用いる。フォントアセットの生成は行わない（範囲外）。
5. **文字体系ゲート**：要求文・既存文言・仕様にCJK（日本語を含む）文字が含まれる場合、`Resources/`配下にその文字体系を含むフォントファイル、または対応するTMPフォントアセットが存在するかを確認する。存在しなければ**停止**し、フォントファイルの配置（ライセンス確認済みのものを`Assets/Resources/Fonts/`へ）を求める。組み込みの`LegacyRuntime.ttf`はCJKを含まず、WebGLではOSフォントへのフォールバックが無いため、代替せずに停止する。
6. **既定値の適用**：参照解像度は1920×1080、入力方式はマウス＋タッチ（キーボード操作は要求時のみ）、マッチ方式は横長で0.5・縦長で0を既定とし、出所を「既定」として報告に列挙する。既定が安全である項目は質問せず先へ進む。
7. **検証段階の決定**：環境変数`UNITY_PATH`が設定され実行可能ならCLI段階、そうでなければ静的検査段階とする。
8. 前提セットを返す。手順5の停止条件に該当した場合は、以降の手順を実行しない。

### F2：UX設計

**入力**：モード、要求文、前提セット。

**出力**：UX設計メモ（画面インベントリ、情報階層、レイアウト方式、状態一覧、フィードバック、導線、追従規則、アクセシビリティ判定）。

**手順**

1. **画面インベントリ**：要求から画面・パネル・部品を列挙し、それぞれの目的（1文）と主要操作（最大3つ）を定める。
2. **情報階層**：各画面で最も重要な情報・操作を1つ選び、視線の起点（左上または中央）に置く。主要操作は1画面に1つ、二次操作は視覚的に弱める。
3. **レイアウト方式の選択**：要素数が固定かつ少数ならアンカー固定、可変・並列ならLayoutGroup、一覧ならScrollRect、と決める。同一階層でアンカー固定とLayoutGroupを混在させない。
4. **状態一覧**：初期・読込中・空・エラー・無効・成功の各状態について、表示の有無と文言を定める。データを扱う画面では空とエラーを省略しない。
5. **フィードバック**：押下可能な要素は押下遷移（色または拡縮）を持つ。破壊的操作は確認を挟む。結果通知はトーストまたはインライン表示とし、モーダルを乱用しない。
6. **導線**：戻る手段を必ず置く。モーダルは背景タップまたは閉じるボタンで閉じられる。キーボード操作が要求される場合はSelectableのナビゲーションを明示設定し、自動ナビゲーションに頼らない。
7. **追従規則**：CanvasScalerは`ScaleWithScreenSize`、参照解像度は前提セットの値、マッチは横長で0.5・縦長で0（幅基準）とする。端に寄せる要素はアンカーで、中央の内容は最大幅を持つコンテナで制御する。
8. **アクセシビリティ判定**：タップ領域は参照解像度で44px四方以上、本文の最小文字サイズは参照解像度で14px以上、前景・背景のコントラスト比は4.5以上、状態の区別は色のみに依らずアイコン・文言を併用する。テーマの色はこの判定を満たす組み合わせのみ採用する。
9. 設計メモを返す。レビュー・改修モードでは既存実装をこのメモと突き合わせ、差分を「所見」として列挙する。

### F3：コード構造設計

**入力**：UX設計メモ、前提セット。

**出力**：クラス構成（画面ビルダー・共通基盤・検証コード）、ファイル配置、依存関係、変更範囲（改修モード）。

**手順**

1. 共通基盤の有無を前提セットから判定し、無ければ`UiTheme`（色・寸法・余白・文字サイズ）、`UiFactory`（Canvas・Panel・Text・Button・Toggle・Slider・ScrollRect・InputField・Dropdownの生成関数）、`UiScreenBase`（Build／Render／Show／Hideの骨格）を`assets/`のテンプレートから起こす。
2. 画面ごとに`<ScreenName>Screen`を定め、`Build`（階層生成。1回のみ）と`Render(state)`（状態反映。何度でも）を分ける。生成後に名前検索（`GameObject.Find`・`transform.Find`）で要素を取り直さず、生成時の参照をフィールドに保持する。
3. ルートは`Canvas`＋`CanvasScaler`＋`GraphicRaycaster`を1組とし、`EventSystem`と入力モジュールはシーンに1つだけ存在するよう、無ければ生成する。
4. ScrollRectはViewport（`RectMask2D`）→Content（`VerticalLayoutGroup`＋`ContentSizeFitter`）の構成に固定する。件数が不明または50件を超える一覧は行の使い回し（プール）を設計に含める。
5. LayoutGroupの子に`ContentSizeFitter`を置かない。子の寸法は`LayoutElement`で与える。`ContentSizeFitter`はLayoutGroupを持つオブジェクト自身にのみ付与する。
6. 角丸・枠線が必要な場合は、実行時に生成した9分割スプライト（手続き的テクスチャ）を`UiFactory`が供給する。Editor専用の組み込みスプライトは参照しない。
7. `UnityEditor`名前空間・`OnGUI`・`AssetDatabase`を実行時コードに含めない。Editorスクリプトは`Assets/Editor/`配下のCLI実行用に限る。
8. **改修モード**：変更範囲を要求に関係するファイル・メソッドに限定する。要求外で下記「設計原則（不変条件）」に反する箇所は変更せず、所見として報告する。
9. 構成を返す。

### F4：実装生成

**入力**：クラス構成、UX設計メモ、前提セット。

**出力**：C#ファイル群、変更差分（改修モード）。

**手順**

1. `assets/`のテンプレートを起点に、テーマ→ファクトリ→基底→画面の順に生成する。既存規約がある場合はテンプレートの命名・配置を既存に合わせて置き換える。
2. 文言はすべて`UiTheme`または画面クラスの定数に集約し、リテラルを散在させない。
3. 色・寸法・文字サイズは`UiTheme`の値のみを用いる。
4. 状態一覧のすべてを`Render(state)`が扱い、未定義状態は例外ではなく「空」表示に倒す。
5. ボタンは`onClick`の登録を`Build`で1回だけ行い、`Render`で再登録しない。
6. 生成後、禁止パターン（`UnityEditor`名前空間の参照、`OnGUI`定義、`AssetDatabase`・`GetBuiltinExtraResource`の使用、`GameObject.Find`・`transform.Find`による生成後の再取得、LayoutGroup配下への`ContentSizeFitter`付与、`EventSystem`生成の欠落、`CanvasScaler`設定の欠落、テーマ外の色リテラル）を自己確認する。
7. ファイル群を返す。

## 設計原則（不変条件）

`references`を読まずに`SKILL.md`のみで実行された場合でも誤った成果物が生成されないよう、以下は`SKILL.md`本文に常設し、`references`へは移さない。すべての手順（F0以降）はこの12項目に反しない範囲で実行する。

1. Editor GUI操作を前提にしない。実行時コードに`UnityEditor`名前空間・`OnGUI`・`AssetDatabase`を含めない。
2. シーンに`EventSystem`と入力モジュールを1つ用意する。無ければ生成する。
3. 各Canvasに`CanvasScaler`（`ScaleWithScreenSize`）と`GraphicRaycaster`を付与する。
4. LayoutGroupの子に`ContentSizeFitter`を付与しない。子の寸法は`LayoutElement`で与える。
5. ScrollRectはViewport（`RectMask2D`）とContent（LayoutGroup＋`ContentSizeFitter`）の構成で組む。
6. 生成した要素の参照はフィールドで保持し、名前検索で取り直さない。
7. CJK文字を表示する場合、対応フォントが`Resources/`またはTMPフォントアセットとして存在しなければ停止する。組み込みフォントで代替しない。
8. TextMeshProのフォントアセットを生成しない。既存アセットがある場合に限りTMPを用いる。
9. 色・寸法・文字サイズ・文言はテーマまたは定数に集約する。
10. 押下可能要素はタップ領域44px以上（参照解像度基準）、コントラスト比4.5以上、状態は色以外でも区別する。
11. 改修モードでは要求範囲外を変更せず所見として報告する。
12. 実施していない検証を実施済みとして報告しない。
