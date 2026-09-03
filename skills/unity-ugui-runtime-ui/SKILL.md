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
