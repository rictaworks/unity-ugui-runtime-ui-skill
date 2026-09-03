# components.md — コンポーネント別の構築手順と落とし穴

`SKILL.md`のF3（コード構造設計）・F4（実装生成）で、ScrollRect・Dropdown・InputField・Slider・Toggleのいずれかを扱うときに読む参照ファイル。個々のuGUIコンポーネントをEditor GUI操作なし・C#コードのみで組み立てる際の手順と、requirements.md 1.1節が挙げる典型的な落とし穴（EventSystemの欠落、CanvasScalerの未設定、LayoutGroupとContentSizeFitterの干渉、ScrollRectの構成不備、フォント未同梱による文字化け、Editor専用APIの混入）を、コンポーネントごとに具体化する。

すべての手順は`SKILL.md`本文の設計原則（不変条件）12項目を満たす前提で書かれている。本ファイルの内容と不変条件が矛盾するように読める場合は不変条件を優先する。既存プロジェクトに`UiFactory`相当のクラスがある場合は、そちらの生成関数を優先し、本ファイルの手順は新規に書き起こす場合の参照として使う（`../assets/UiFactory.cs.tmpl`が実装例）。

## 目次

1. [共通の落とし穴](#共通の落とし穴)
2. [Canvas / CanvasScaler / GraphicRaycaster](#canvas--canvasscaler--graphicraycaster)
3. [EventSystem](#eventsystem)
4. [RectTransform（アンカー・ピボット）](#recttransformアンカーピボット)
5. [LayoutGroup系 / ContentSizeFitter / LayoutElement](#layoutgroup系--contentsizefitter--layoutelement)
6. [Image / RawImage](#image--rawimage)
7. [Text](#text)
8. [Button](#button)
9. [Toggle](#toggle)
10. [Slider](#slider)
11. [Scrollbar](#scrollbar)
12. [ScrollRect](#scrollrect)
13. [Dropdown](#dropdown)
14. [InputField](#inputfield)
15. [Mask / RectMask2D](#mask--rectmask2d)
16. [Selectableのナビゲーション](#selectableのナビゲーション)
17. [コンポーネント横断の自己確認表](#コンポーネント横断の自己確認表)

---

## 共通の落とし穴

個別コンポーネントの前に、requirements.md 1.1節が挙げる6つの落とし穴を、発生条件と対処に分けて示す。以降の各節では、この6つのうちどれに関係するかを都度参照する。

| 落とし穴 | 発生条件 | 対処 |
|---|---|---|
| EventSystemの欠落 | シーンに`EventSystem`が1つも無いままButton等を配置し、クリックが一切反応しない | 画面生成の起点で`Object.FindFirstObjectByType<EventSystem>()`により存在確認し、無ければ`EventSystem`＋入力モジュールを生成する（不変条件2）。名前検索は使わない |
| CanvasScalerの未設定 | `CanvasScaler`を既定の`ConstantPixelSize`のまま使い、解像度が変わると要素の実寸が変わらずレイアウトが破綻する | `CanvasScaler.uiScaleMode`を`ScaleWithScreenSize`にし、`referenceResolution`と`matchWidthOrHeight`を明示する（不変条件3） |
| LayoutGroupとContentSizeFitterの干渉 | LayoutGroupの子オブジェクトに`ContentSizeFitter`を付けてしまい、親のLayoutGroupと子のFitterが互いのサイズ計算を上書きし続けてレイアウトが振動・崩壊する | `ContentSizeFitter`はLayoutGroupを持つオブジェクト自身にのみ付与する。子の寸法は`LayoutElement`で与える（不変条件4） |
| ScrollRectの構成不備 | Viewportに`RectMask2D`が無くマスクされない、Contentに`ContentSizeFitter`が無く内容が伸びない、`ScrollRect.content`／`viewport`の参照が未設定、など | Viewport（`RectMask2D`のみ）→Content（LayoutGroup＋`ContentSizeFitter`）の構成に固定する（不変条件5、詳細は[ScrollRect](#scrollrect)節） |
| フォント未同梱による文字化け | CJK文字を含む文言を組み込みフォント（`LegacyRuntime.ttf`等）で表示し、WebGLではOSフォントへのフォールバックが無いため豆腐（□）表示になる | CJKを扱う場合は`Resources/`配下の対応フォントまたはTMPフォントアセットの存在を確認してから`Text`を生成する。存在しなければ停止する（不変条件7、詳細は`references/text-and-fonts.md`） |
| Editor専用APIの混入 | `UnityEditor`名前空間、`OnGUI`、`AssetDatabase`、`EditorGUIUtility.GetBuiltinExtraResource`等をランタイムコードに書いてしまい、ビルドで壊れる／実機で動かない | 実行時コードでは`UnityEditor`を一切参照しない。組み込みスプライトの代わりに実行時生成の9分割スプライトを使う（不変条件1、[Image / RawImage](#image--rawimage)節） |

これに加え、コンポーネント固有の落とし穴として以下が繰り返し起きる。

- **参照の取り直し**：生成直後は正しく動いていたコードが、後日の改修で`transform.Find("Handle")`のような名前検索を追加され、階層変更時に無言で壊れる。生成関数の戻り値（構造体・フィールド）で参照を保持する（不変条件6）。
- **onClick／onValueChangedの多重登録**：`Render`が呼ばれるたびに`AddListener`を実行し、1回のクリックでコールバックが複数回発火する。リスナー登録は`Build`で1回に限る（5.5節手順5）。
- **色・寸法のリテラル散在**：コンポーネント生成のたびに`new Color32(...)`や`44f`のようなリテラルを書き、テーマ変更時に全箇所を洗い出す羽目になる。`UiTheme`の定数のみを参照する（不変条件9）。

---

## Canvas / CanvasScaler / GraphicRaycaster

**構築手順**

1. `GameObject`に`Canvas`・`CanvasScaler`・`GraphicRaycaster`を一括で付与する（`typeof(...)`を並べたコンストラクタが取り違えを防ぐ）。
2. `Canvas.renderMode`は`ScreenSpaceOverlay`を既定とする。3Dシーンに重ねる要求がある場合のみ`ScreenSpaceCamera`を検討し、その場合は`worldCamera`の設定漏れに注意する。
3. `CanvasScaler.uiScaleMode = ScaleMode.ScaleWithScreenSize`、`referenceResolution`は前提セットの値、`screenMatchMode = MatchWidthOrHeight`、`matchWidthOrHeight`は横長0.5・縦長0（`SKILL.md`のF2手順7）とする。
4. 複数のCanvasを重ねる場合（ベース画面とモーダル等）は`sortingOrder`を明示し、暗黙の描画順に依存しない。

**落とし穴**

- `CanvasScaler`を追加し忘れ、`ConstantPixelSize`のまま解像度が変わるとレイアウトが破綻する（共通の落とし穴参照）。
- モーダル用Canvasの`sortingOrder`を指定せず、生成順に依存して背面に隠れる。
- `GraphicRaycaster`の付け忘れにより、見た目は正しいのにクリックが一切通らない（EventSystemの欠落と誤認しやすいので切り分けること）。

---

## EventSystem

**構築手順**

1. 画面生成の最初に、型検索（`Object.FindFirstObjectByType<EventSystem>()`）で既存の`EventSystem`を確認する。
2. 存在しなければ`EventSystem`と入力モジュール（既定は`StandaloneInputModule`）を1つ生成する。
3. プロジェクトがInput Systemパッケージのみで動作する場合は、呼び出し側で`InputSystemUIInputModule`に置き換える。追加パッケージの導入判断はプロジェクト側の既存規約に従う。

**落とし穴**

- `EventSystem`が無いままButton・Toggle・Slider・InputField・Dropdownを配置し、クリック・タップが一切反応しない（最も頻度の高い落とし穴）。
- 複数画面を独立に生成するコードが、画面ごとに`EventSystem`を重複生成し、入力が二重処理される。生成前の存在確認を省略しない。
- `GameObject.Find("EventSystem")`のような名前検索で存在確認を行い、名前を変更されると検出できなくなる。型検索を使う（不変条件6）。

---

## RectTransform（アンカー・ピボット）

**構築手順**

1. 親いっぱいに広げる要素は`anchorMin = (0,0)`・`anchorMax = (1,1)`・`offsetMin/offsetMax = (0,0)`・`pivot = (0.5, 0.5)`に統一する（`UiFactory.StretchFull`相当のヘルパーに集約する）。
2. 端に固定する要素（右上の閉じるボタン等）はアンカーを対象の角に寄せ、`pivot`も同じ角に合わせて`sizeDelta`で寸法を与える。
3. 中央寄せで最大幅を持たせたい要素（本文カラム等）は、`anchorMin=(0.5,y)`・`anchorMax=(0.5,y)`＋`sizeDelta`ではなく、`LayoutElement.preferredWidth`と親の`HorizontalLayoutGroup`の組み合わせで最大幅を制御する方が、解像度追従時に破綻しにくい。
4. 同一階層内でアンカー固定の子とLayoutGroup制御下の子を混在させない（`SKILL.md`F2手順3、`layout.md`参照）。

**落とし穴**

- アンカーとピボットの不一致（例：`anchorMin/Max`は中央、`pivot`は左上のまま）により、解像度が変わると意図しない方向にずれる。
- `sizeDelta`と`anchorMin/Max`を同時にストレッチ設定のまま変更し、実際の矩形サイズが0または負になる。
- LayoutGroup配下の子に対して直接`anchoredPosition`や`sizeDelta`を設定し、LayoutGroupの再計算で毎フレーム上書きされて操作が反映されない（[LayoutGroup系](#layoutgroup系--contentsizefitter--layoutelement)節参照）。

---

## LayoutGroup系 / ContentSizeFitter / LayoutElement

**構築手順**

1. 要素数が可変・並列（横並びのボタン列、縦積みのカード等）なら`HorizontalLayoutGroup`／`VerticalLayoutGroup`を使う。要素数が固定かつ少数ならアンカー固定を優先し、LayoutGroupを持ち出さない（`SKILL.md`F2手順3）。
2. `childControlWidth`／`childControlHeight`／`childForceExpandWidth`／`childForceExpandHeight`は、子の寸法をLayoutGroupに委ねるか`LayoutElement`で個別指定するかを画面ごとに決め打ちし、暗黙の既定値に頼らない。
3. 子の最小・推奨・最大寸法は`LayoutElement`（`minWidth`／`minHeight`／`preferredWidth`／`preferredHeight`／`flexibleWidth`）で与える。
4. コンテナ自身の外形をコンテンツ量に合わせて伸縮させたい場合のみ、そのコンテナ自身に`ContentSizeFitter`を付与する。
5. 余白・間隔（`padding`・`spacing`）は`UiTheme.Sizes`の段階値のみを使う。

**落とし穴（LayoutGroupとContentSizeFitterの干渉）**

- LayoutGroupの**子**に`ContentSizeFitter`を付けると、LayoutGroupが子のサイズを制御しようとする一方でFitterも同じ子のサイズを書き換え、1〜2フレームおきにサイズが往復して見た目が揺れる、またはレイアウトが固まる。`ContentSizeFitter`はLayoutGroupを**持つ側**にのみ付与する（不変条件4）。
- `childControlWidth = false`のままLayoutGroupを使い、子の`RectTransform`を直接操作するコードと共存させ、どちらが最終的な寸法を決めているか分からなくなる。
- 深いネスト（LayoutGroup配下にLayoutGroup配下に…）で`ContentSizeFitter`を各階層に置き、再計算コストが増える上に伝播順序が不定になる。伸縮が必要な階層を1つに絞る。
- `LayoutElement`を付けずに子の寸法をゼロのままLayoutGroupに渡し、要素が潰れて見えなくなる。

---

## Image / RawImage

**構築手順**

1. 単色パネル・アイコンには`Image`を使う。外部テクスチャ（カメラ映像・動的生成テクスチャ等）を貼る場合のみ`RawImage`を使う。
2. 角丸・枠線が必要な場合は、実行時に手続き的に生成した9分割スプライト（`Sprite.Create`＋`border`指定）を`Image.type = Image.Type.Sliced`で使う。
3. マスク専用（可視背景を持たない）の`Image`は`color = Color.clear`とし、`raycastTarget`の要否を明示する（ScrollRectのViewport等）。
4. `RawImage`は`uvRect`のデフォルト（`(0,0,1,1)`）を確認し、意図しないトリミング・反転が起きていないか確認する。

**落とし穴（Editor専用APIの混入）**

- 角丸表現のために`EditorGUIUtility.GetBuiltinExtraResource<Sprite>("UI/Skin/...")`のようなEditor専用APIを使い、ビルド後に例外またはnull参照になる。実行時生成のスプライトに置き換える（不変条件1、F3手順6）。
- `Resources.Load`でEditor限定フォルダ（`Editor/`配下）のアセットを参照し、ビルドに含まれず実機で欠落する。
- マスク用`Image`の`raycastTarget`をtrueのままにし、意図しない位置でクリックを奪う。

---

## Text

**構築手順**

1. 既定は`UnityEngine.UI.Text`。既存コードが`TMPro`を使用し、対象文字体系をカバーするTMPフォントアセットが既にある場合のみTextMeshProを使う（不変条件8、`text-and-fonts.md`）。
2. `font`は呼び出し側（テキスト方式解決の結果）から渡し、生成関数自身はフォント解決を行わない。
3. `fontSize`は`UiTheme.TextSizes`の段階値のみを使い、本文相当は14px以上を確保する（不変条件10）。
4. `horizontalOverflow = Wrap`・`verticalOverflow = Truncate`を既定とし、想定外の文字数でレイアウトが突き破られないようにする。長文を確実に収めたい場合は`RectTransform`側に十分な高さを確保するか、ScrollRect配下に置く。
5. 装飾目的のみ（クリック不要）のテキストは`raycastTarget = false`にし、無駄なレイキャスト対象を増やさない。

**落とし穴（フォント未同梱による文字化け）**

- CJK文字体系を組み込みフォント（`LegacyRuntime.ttf`）で表示し、WebGLはOSフォントへのフォールバックが無いため豆腐（□）表示になる。生成前に文字体系ゲート（不変条件7）を通す。
- `fontSize`をリテラルで散らし、後からテーマの文字サイズ段階を変えても一部だけ変わらない。
- `verticalOverflow = Truncate`のまま高さが不足する`RectTransform`を割り当て、文言が入るたびに末尾が欠ける。状態文言（エラー・空状態等）は特に長さが変動するため注意する。

---

## Button

**構築手順**

1. `Image`（背景）＋`Button`を1つの`GameObject`に付与し、`Button.targetGraphic`を背景`Image`に設定する。
2. タップ領域は`LayoutElement.minWidth`／`minHeight`を`UiTheme.Sizes.TapMinSize`（44px）以上にする（不変条件10）。
3. ラベルは子の`Text`として生成し、`raycastTarget = false`にして親のクリック判定を邪魔しないようにする。
4. `onClick.AddListener(...)`は`Build`で1回だけ行う。`Render`から再度呼ばない（5.5節手順5）。
5. 押下遷移（色または拡縮）は`Button.transition`（既定`ColorTint`）の`colors`をテーマ色で設定するか、`ScaleTransition`相当を独自実装する場合も色をテーマから取る。
6. 破壊的操作（削除・上書き等）に紐づくボタンは、直接の実処理を呼ばず確認ダイアログを経由させる（F2手順5）。

**落とし穴**

- `Render(state)`内で毎回`onClick.AddListener`し、1クリックでコールバックがN回発火する（Nは`Render`呼び出し回数）。
- `targetGraphic`未設定のまま`transition = ColorTint`にし、押下しても見た目が変化しない。
- 無効状態を`interactable = false`だけで表現し、色の変化のみに依存する（不変条件10違反）。ラベル変更やアイコン併用も検討する。
- タップ領域を背景`Image`の見た目サイズだけで確保し、余白込みの実クリック領域が44px未満になる。

---

## Toggle

**構築手順**

1. `Toggle`本体には`LayoutElement.minHeight`で`TapMinSize`を確保する。
2. 背景（未チェック時の枠）とチェックマークを別の子`Image`として生成し、`Toggle.targetGraphic`＝背景、`Toggle.graphic`＝チェックマークに割り当てる。
3. ラベルは背景の右側に配置し、`offsetMin.x`をチェック領域の幅＋余白分だけ空ける。
4. `isOn`の初期値は呼び出し側から渡し、`onValueChanged.AddListener`は`Build`で1回登録する。
5. 状態（オン・オフ・無効）の区別を色だけに頼らない。チェックマークの表示有無（形状差）で担保できているか確認する。

**落とし穴**

- 背景とチェックマークを1つの`Image`で兼用し、オン・オフの表現が色反転のみになる（色以外の区別が無い、不変条件10違反）。
- ラベル領域の`offsetMin`計算を怠り、チェック領域とラベルが重なる。
- 複数のToggleでグループ排他（ラジオボタン相当）が必要な場合に`Toggle.group`（`ToggleGroup`）の割り当てを忘れ、複数同時オンを許してしまう。

---

## Slider

**構築手順**

1. `Slider`本体に`LayoutElement.minHeight = TapMinSize`を設定する。
2. Background（`Image`、全面ストレッチ）→FillArea→Fill（`Image`、`anchorMax.x`を0起点で可変）→HandleArea→Handle（`Image`、`sizeDelta`固定）の階層で構成する。
3. `Slider.fillRect`／`handleRect`／`targetGraphic`（Handleの`Image`）を明示的に割り当てる。
4. `minValue`／`maxValue`／`value`の初期値を呼び出し側から受け取り、`onValueChanged.AddListener`は`Build`で1回登録する。
5. Handleの当たり判定・見た目サイズが`TapMinSize`未満にならないよう、`Handle`単体でなく`Slider`全体の縦幅で確保する（Handleそのものを44px四方にする必要はないが、操作可能領域の縦幅は確保する）。

**落とし穴**

- `fillRect`の`anchorMax`を初期化し忘れ、Fillが常に全幅または常に0幅のまま表示される。
- Handleの`Image`を`targetGraphic`に割り当て忘れ、`Selectable`としてのハイライト（押下遷移）が効かない。
- 縦方向Sliderが必要な要求で`direction`を変更せず、`fillRect`のアンカー設定だけ横向きのまま流用して見た目が壊れる。

---

## Scrollbar

**構築手順**

1. ScrollRect付属の暗黙スクロールバーに頼らず、明示的に`Scrollbar`コンポーネントを持つ子オブジェクト（Background→Sliding Area→Handle）として生成する場合は、`ScrollRect.verticalScrollbar`／`horizontalScrollbar`に割り当てる。
2. `Scrollbar.direction`をScrollRectのスクロール方向と一致させる。
3. `Scrollbar.size`はScrollRectが自動更新する前提のため、初期値は0より大きい暫定値（例：1）にしておき、初期表示のちらつきを避ける。
4. 常時表示が不要な場合は`ScrollRect.verticalScrollbarVisibility = AutoHideAndExpandViewport`等を検討するが、採用するとViewportの実効幅が変わるため、[ScrollRect](#scrollrect)側の幅計算に影響が無いか確認する。

**落とし穴**

- `Scrollbar`を生成しただけで`ScrollRect.verticalScrollbar`に割り当てず、スクロールバーの見た目とスクロール位置が連動しない。
- `AutoHideAndExpandViewport`採用時にViewportの`RectMask2D`と`ContentSizeFitter`の再計算タイミングがずれ、スクロールバー出現時に一瞬だけ内容がはみ出す。

---

## ScrollRect

ScrollRectはrequirements.md 1.1節が名指しする落とし穴（構成不備）の中心であり、不変条件5に直結する。以下の構成を必ず守る。

**構築手順（固定構成）**

1. ルート：`ScrollRect`本体。親いっぱいにストレッチする。
2. **Viewport**：ルート直下の子。`RectMask2D`のみを持ち、`ContentSizeFitter`は**持たせない**。マスク描画専用のため`Image.color = Color.clear`で構わない。
3. **Content**：Viewport直下の子。`VerticalLayoutGroup`（一覧の並び方向に応じて`HorizontalLayoutGroup`）と`ContentSizeFitter`を**自身に**持つ。アンカーは上端基準（`anchorMin=(0,1)`・`anchorMax=(1,1)`・`pivot=(0.5,1)`）とし、横幅は親に追従、縦幅はコンテンツ量で決まるようにする。
4. Contentの`ContentSizeFitter`は`horizontalFit = Unconstrained`・`verticalFit = PreferredSize`を既定とする（横スクロール一覧の場合は逆）。
5. `ScrollRect.viewport`／`content`を明示的に割り当てる（暗黙のTransform順に依存しない）。
6. 行アイテムはContent配下に生成し、行自身に`ContentSizeFitter`を付けない（LayoutGroupの子になるため）。行の寸法は`LayoutElement`で与える。
7. 件数が不明または50件を超える一覧は、行の使い回し（プール）を設計に含める（`SKILL.md`F3手順4、詳細は`references/webgl-runtime.md`）。プールする場合、非表示行を`SetActive(false)`にするだけでなくContent内の並び順（`SetSiblingIndex`）も更新し、LayoutGroupの再計算に委ねる。

**落とし穴**

- Viewportに`RectMask2D`を付け忘れ、Content内の行がViewport外にもそのまま描画される。
- Viewportに`ContentSizeFitter`を付けてしまい、Viewport自体がContentの大きさに合わせて広がろうとし、マスクの意味が失われる（LayoutGroupとContentSizeFitterの干渉の一種）。
- Contentの`ContentSizeFitter`を付け忘れ、行を追加してもContentの高さが更新されずスクロール範囲が伸びない。
- `ScrollRect.content`にViewportを、`viewport`にContentを取り違えて割り当てる。
- Content配下の行に`ContentSizeFitter`を付与し、LayoutGroup（Content）との干渉でスクロール中に行の高さが揺れる。
- 横スクロールのつもりで`VerticalLayoutGroup`のまま`horizontal = true`にし、行が縦積みのまま横に伸びない。
- 50件超の一覧を全件生成し、WebGLでの初期構築が数百ms〜数秒かかる（`webgl-runtime.md`参照）。

---

## Dropdown

DropdownはScrollRectの構成をテンプレート（展開時のリスト）内部に含むため、[ScrollRect](#scrollrect)の落とし穴がそのまま適用される。

**構築手順**

1. 本体：`Image`（背景）＋`Dropdown`。`LayoutElement.minHeight = TapMinSize`。
2. キャプション用`Text`を子に生成し、`Dropdown.captionText`に割り当てる。
3. Template：本体の下に重ねて配置する子（既定で`SetActive(false)`）。内部はScrollRectと同じViewport（`RectMask2D`）→Content（`VerticalLayoutGroup`＋`ContentSizeFitter`）構成にする。
4. Item：Content配下に1件分のテンプレート（`Toggle`＋背景`Image`＋チェックマーク`Image`＋ラベル`Text`）を生成する。`Dropdown`が複製して選択肢数ぶん使う。
5. `Dropdown.template`／`captionText`／`itemText`を明示的に割り当て、`options`を`Dropdown.OptionData`で構築する。
6. `onValueChanged.AddListener`は`Build`で1回登録する。

**落とし穴**

- Templateの初期状態を表示のままにし、生成直後に展開UIが常時見えてしまう（`SetActive(false)`忘れ）。
- Template内部のViewportに`RectMask2D`を付け忘れ、展開時に選択肢がリスト範囲外までそのまま表示される。
- `itemText`を割り当てず、選択肢のラベルが空のまま表示される。
- 選択肢が多い（数十件以上）場合にTemplateの初期高さ（`sizeDelta`）を固定値のまま放置し、画面下端で切れる、または過剰に長くなる。参照解像度基準で上限を設ける。
- キーボード操作が要求されているのに、Dropdown展開中のフォーカス遷移を確認せず、選択肢間の移動ができない（[Selectableのナビゲーション](#selectableのナビゲーション)節参照）。

---

## InputField

**構築手順**

1. 本体：`Image`（背景）＋`InputField`。`LayoutElement.minHeight = TapMinSize`。
2. TextArea：`RectMask2D`を持つ子を挟み、その中にプレースホルダー用`Text`と入力値表示用`Text`を重ねて生成する。左右に`UiTheme.Sizes.SpacingSmall`程度の内側余白を確保する。
3. `InputField.textComponent`／`placeholder`を明示的に割り当てる。
4. プレースホルダーは`FontStyle.Italic`等、色以外の手段でも入力値と区別できるようにする。
5. `contentType`（数値のみ・パスワード等）が要求にある場合はここで設定する。既定は`Standard`。
6. `onValueChanged.AddListener`は`Build`で1回登録する。バリデーション結果（エラー状態）は`Render(state)`側で表示を切り替える。

**落とし穴**

- TextAreaに`RectMask2D`を付け忘れ、入力文字が長くなると背景の外まで描画される。
- `placeholder`を`textComponent`と同じ`Text`に割り当ててしまい、入力するとプレースホルダーごと消える／文字が二重に見える。
- CJK入力を想定する要求で、対応フォントの確認（不変条件7）を怠り入力中の文字が豆腐表示になる。
- エラー状態を枠線色の変化のみで表現し、色以外の区別（アイコン・文言）を伴わない（不変条件10）。
- キーボードでのフォーカス移動時、次のフィールドへの`Selectable.navigation`が既定（Automatic）のまま画面外の要素へ飛ぶ。

---

## Mask / RectMask2D

**構築手順**

1. 矩形でのクリッピングのみが必要な場合（ScrollRectのViewport等）は`RectMask2D`を使う。負荷が軽く、`Image`が無くてもマスクとして機能する（ただし本テンプレートの慣例としてマスク専用の`Image`を`color = Color.clear`で伴わせ、意図を明示する）。
2. 円形・任意形状のマスクが必要な場合のみ`Mask`＋`Image`（`Show Mask Graphic`の要否を確認）を使う。`Mask`はステンシルバッファを使うため、`RectMask2D`より負荷が高い点を性能要求（`webgl-runtime.md`）と照らして判断する。
3. マスク用`Image`の`raycastTarget`は用途に応じて明示する（クリックを透過させたいなら`false`）。

**落とし穴**

- `RectMask2D`で足りる矩形クリッピングに`Mask`を多用し、WebGLでの描画負荷が不要に増える。
- `Mask`の`Show Mask Graphic = false`にしたつもりが、マスク用`Image`の`color`を不透明のまま残し、意図せず背景として見えてしまう。
- ネストした`RectMask2D`（マスクの中にマスク）を多用し、意図しない二重クリッピングでコンテンツが欠ける。

---

## Selectableのナビゲーション

キーボード・ゲームパッド操作が要求される場合のみ扱う（4.1節・入力方式）。マウス・タッチのみの要求では本節は対象外とする。

**構築手順**

1. 既定の自動ナビゲーション（`Navigation.Mode.Automatic`）は、階層構造や生成順によって意図しない移動順になりやすいため、キーボード操作が要求される画面では`Navigation.Mode.Explicit`にし、`selectOnUp`／`Down`／`Left`／`Right`を明示的に設定する（`SKILL.md`F2手順6）。
2. フォーカス順は情報階層（F2手順2）で定めた視線の起点から、画面の主要導線に沿って設定する。
3. 初期フォーカスが必要な場合は`EventSystem.current.SetSelectedGameObject(...)`を`Build`完了後・`Show`のタイミングで1回呼ぶ。
4. モーダル表示中は背後の画面のSelectableにフォーカスが移らないよう、モーダル内で閉じたナビゲーション環（Tab/方向キーがモーダル外に出ない）を構成するか、モーダル表示中は背後の`CanvasGroup.interactable = false`にする。

**落とし穴**

- `Automatic`のまま放置し、ScrollRect内の行を動的に増減させるとフォーカス順が生成順に依存して毎回変わる。
- モーダルを開いたまま背後のSelectableにキーボードでフォーカスが移り、閉じたはずのダイアログの裏で操作が成立してしまう。
- 明示ナビゲーションを設定したのに、対象のSelectableが後から`Destroy`されて参照切れの`Navigation`が残る。行の使い回し（プール）を行う画面では、非表示化と再表示のたびにナビゲーションの参照を張り直す。

---

## コンポーネント横断の自己確認表

F4（実装生成）手順6の自己確認、およびF5（検証）の静的検査（`scripts/lint_ugui_csharp.py`）と対応する。生成後、対象コンポーネントごとに該当行を確認する。

| コンポーネント | 確認項目 |
|---|---|
| Canvas | `CanvasScaler`が`ScaleWithScreenSize`か、`GraphicRaycaster`が付与されているか |
| EventSystem | 型検索で存在確認しているか、名前検索で取得していないか |
| Button/Toggle/Slider/InputField/Dropdown | タップ領域44px以上か、リスナー登録が`Build`で1回のみか |
| LayoutGroupの子 | `ContentSizeFitter`を持っていないか、寸法を`LayoutElement`で与えているか |
| ScrollRect/Dropdownのテンプレート | Viewportに`RectMask2D`があるか、Contentに`ContentSizeFitter`があるか、`viewport`/`content`の割り当てが正しいか |
| Text | フォントがCJK対応済みか（対象文字体系がある場合）、文字サイズが14px以上か |
| 色・寸法・文言 | `UiTheme`の定数のみを参照しているか、リテラルが残っていないか |
| 全体 | `UnityEditor`名前空間・`OnGUI`・`AssetDatabase`を参照していないか |
