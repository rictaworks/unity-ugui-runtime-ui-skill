# layout.md — アンカー・LayoutGroup・ContentSizeFitter・追従規則

`SKILL.md`の読み込み条件（LayoutGroupまたは可変要素数の画面を設計するとき、レイアウト崩れの改修のとき）に該当した場合にのみ読む。ここに書く内容は`SKILL.md`本文の設計原則（不変条件）を補足するものであり、矛盾する場合は`SKILL.md`側が正である。

## 目次

1. [この参照ファイルの位置づけ](#この参照ファイルの位置づけ)
2. [アンカーとピボットの使い方](#アンカーとピボットの使い方)
3. [LayoutGroup系の選択基準](#layoutgroup系の選択基準)
4. [同一階層でアンカー固定とLayoutGroupを混在させない](#同一階層でアンカー固定とlayoutgroupを混在させない)
5. [ContentSizeFitterの正しい付与範囲](#contentsizefitterの正しい付与範囲)
6. [ScrollRectのレイアウト構成](#scrollrectのレイアウト構成)
7. [追従規則（CanvasScaler）](#追従規則canvasscaler)
8. [レイアウト崩れの診断手順（改修モード）](#レイアウト崩れの診断手順改修モード)
9. [アンチパターン早見表](#アンチパターン早見表)

---

## この参照ファイルの位置づけ

`SKILL.md`の設計原則（不変条件）のうち、本ファイルが特に補足するのは次の3項目である。番号は`SKILL.md`「設計原則（不変条件）」の通し番号に対応する。

- **不変条件4**：LayoutGroupの子に`ContentSizeFitter`を付与しない。子の寸法は`LayoutElement`で与える。
- **不変条件5**：ScrollRectはViewport（`RectMask2D`）とContent（LayoutGroup＋`ContentSizeFitter`）の構成で組む。
- **不変条件9**：色・寸法・文字サイズ・文言はテーマまたは定数に集約する。

本ファイルの図・コード例で使う寸法・色のリテラルは、実装では必ず`UiTheme`（`UiTheme.Sizes`・`UiTheme.Colors`・`UiTheme.TextSizes`）に置き換える。本文中の数値はあくまで説明用であり、そのまま生成コードに書き写さない。

## アンカーとピボットの使い方

### 使う場面（F2手順3）

要素数が**固定かつ少数**の画面・パネルでは、`RectTransform`のアンカー・ピボットのみで配置する。可変・並列な要素、一覧はこの節ではなくLayoutGroup（次節）・ScrollRectを使う。

### アンカーの基本パターン

| 用途 | `anchorMin` | `anchorMax` | 備考 |
|---|---|---|---|
| 親いっぱいに広げる（ストレッチ） | `(0, 0)` | `(1, 1)` | `offsetMin`/`offsetMax`で余白を与える |
| 左上に固定 | `(0, 1)` | `(0, 1)` | `pivot = (0, 1)`と揃える |
| 右上に固定 | `(1, 1)` | `(1, 1)` | `pivot = (1, 1)`と揃える |
| 下端に幅いっぱい・高さ固定 | `(0, 0)` | `(1, 0)` | `pivot = (0.5, 0)`、`sizeDelta.y`で高さ指定 |
| 中央に固定サイズ | `(0.5, 0.5)` | `(0.5, 0.5)` | `pivot = (0.5, 0.5)`、`sizeDelta`で寸法指定 |

ピボットは「アンカー矩形内でのオブジェクト自身の基準点」であり、アンカーの`min`/`max`と一致する側に揃えるのが基本である（例：右上固定なら`anchorMin = anchorMax = (1, 1)`かつ`pivot = (1, 1)`）。ピボットをアンカーと不一致のまま`anchoredPosition`を動かすと、`CanvasScaler`のスケール変化時に意図しない位置ズレが生じる。

`UiFactory`の`StretchFull`（親いっぱいに広げる共通ヘルパー）は、`anchorMin = Vector2.zero`・`anchorMax = Vector2.one`・`offsetMin = offsetMax = Vector2.zero`・`pivot = (0.5, 0.5)`を一括設定する。同種の固定パターンを画面クラスで繰り返す場合は、同様の小関数に切り出し、リテラルの重複を避ける。

### 端寄せ要素と中央コンテンツの使い分け（F2手順7）

- 画面の端（ヘッダー・フッター・戻るボタン・トースト）に寄せる要素は**アンカーで端に固定**する。解像度・アスペクト比が変わっても端からの距離が保たれる。
- 画面中央の主要コンテンツは、**最大幅を持つコンテナ**（`LayoutElement.preferredWidth`または`RectTransform.sizeDelta`の上限）で中央寄せにする。ストレッチだけで広げると、超横長（21:9等）で行の折り返し・タップ領域の間延びが起きる。

```csharp
// 中央コンテンツを最大幅で制限し、それより広い画面では左右に余白を残す例。
// ContentMaxWidth はこの画面向けに UiTheme.Sizes へ追加した定数（不変条件9）で、
// リテラルをコード中に直書きしない。
var contentRect = (RectTransform)contentGo.transform;
contentRect.anchorMin = new Vector2(0.5f, 0f);
contentRect.anchorMax = new Vector2(0.5f, 1f);
contentRect.pivot = new Vector2(0.5f, 0.5f);
var contentLayoutElement = contentGo.AddComponent<LayoutElement>();
contentLayoutElement.preferredWidth = UiTheme.Sizes.ContentMaxWidth;
```

## LayoutGroup系の選択基準

### 選択基準（F2手順3）

| 状況 | 選択 |
|---|---|
| 要素数が固定・少数（2〜3個程度）で位置関係が変わらない | アンカー固定（前節） |
| 要素が横並びで、数や表示が要求に応じて変わる | `HorizontalLayoutGroup` |
| 要素が縦並びで、数や表示が要求に応じて変わる | `VerticalLayoutGroup` |
| 同一寸法のセルを格子状に並べる（一覧のカード表示等） | `GridLayoutGroup` |
| 件数が可変で縦・横にスクロールする一覧 | ScrollRect＋`VerticalLayoutGroup`（[ScrollRectのレイアウト構成](#scrollrectのレイアウト構成)を参照） |

`HorizontalLayoutGroup`・`VerticalLayoutGroup`と`GridLayoutGroup`は、要素の並び方が一次元（横一列・縦一列）か二次元（格子）かで選ぶ。並び順を保ちつつ折り返しも必要な場合（可変幅で折り返す一覧等）は、`GridLayoutGroup`の`constraint`を`FlexibleRow`にするか、要求が複雑になる場合は一次元LayoutGroupの入れ子で代替できないか先に検討する。

### 主要プロパティの意味

- `childControlWidth`／`childControlHeight`：`true`にするとLayoutGroupが子の`RectTransform`の幅・高さを直接書き換える。`false`の場合、子は自身のサイズを保持する（`LayoutElement`で与えた値がそのまま使われる）。
- `childForceExpandWidth`／`childForceExpandHeight`：`true`にすると、余った領域を子に均等配分して広げる。一覧の行のように「幅は広げるが高さは内容分だけ」という構成では、`childForceExpandWidth = true`・`childForceExpandHeight = false`の組み合わせが典型である（`UiFactory.CreateScrollRect`のContent設定を参照）。
- `spacing`：子同士の間隔。`UiTheme.Sizes`の余白段階（`SpacingXSmall`〜`SpacingXLarge`）から選ぶ。
- `padding`：LayoutGroup自身の内側余白。`RectOffset`の4方向すべてを`UiTheme.Sizes`の値から構成する。
- `childAlignment`：子の配置基準点。中身が領域より小さい場合の寄せ方を決める。

### 子の寸法は`LayoutElement`で与える

LayoutGroupの子がとる寸法（最小・推奨・柔軟）は、子オブジェクトに付与した`LayoutElement`の`minWidth`/`minHeight`・`preferredWidth`/`preferredHeight`・`flexibleWidth`/`flexibleHeight`で指定する。`UiFactory.CreateButton`が`LayoutElement.minWidth`/`minHeight`に`UiTheme.Sizes.TapMinSize`を設定しているのがこの例であり、押下可能要素をLayoutGroup配下に置いてもタップ領域の下限（不変条件10）が保たれる。

```csharp
// HorizontalLayoutGroup配下の子（例：ツールバーの3ボタン）。
var toolbarGo = new GameObject("Toolbar", typeof(RectTransform), typeof(HorizontalLayoutGroup));
var toolbarLayout = toolbarGo.GetComponent<HorizontalLayoutGroup>();
toolbarLayout.childAlignment = TextAnchor.MiddleCenter;
toolbarLayout.childForceExpandWidth = false;
toolbarLayout.childForceExpandHeight = false;
toolbarLayout.childControlWidth = false;
toolbarLayout.childControlHeight = false;
toolbarLayout.spacing = UiTheme.Sizes.SpacingSmall;

// 子（ボタン）は UiFactory.CreateButton が LayoutElement を自前で付与するため、
// ここで改めて寸法を指定する必要はない。ContentSizeFitter は toolbarGo にも
// 子にも付与しない（要素数が固定のため、LayoutGroupの自動採寸で十分）。
```

## 同一階層でアンカー固定とLayoutGroupを混在させない

同じ親（同一階層）の子要素に対して、一部はアンカーで個別配置し、一部はLayoutGroupに並びを任せる、という混在をしない（F2手順3）。LayoutGroupは自身の直接の子すべての`RectTransform`を管理対象とするため、アンカー固定を意図した子がいても位置・寸法を上書きされ、レイアウト崩れの典型的な原因になる。

- 一部の子だけ固定位置にしたい場合は、固定したい子をLayoutGroupの**外**（親のさらに親、または兄弟のオーバーレイ層）に置く。
- LayoutGroup配下で見た目上「効かせたくない」子がある場合は、`LayoutElement.ignoreLayout = true`を明示するか、そもそもその子を別階層に分離する。「ignoreLayoutで無効化して同居させる」は例外的な逃げ道であり、設計段階では階層分離を優先する。

```
NG（同一階層で混在）:
Panel (アンカー固定の子と LayoutGroup 前提の子が同居)
├── Header      … アンカーで左上固定のつもり
├── ButtonRow   … HorizontalLayoutGroupで並べたい
└── FooterNote  … アンカーで下端固定のつもり
    ※ Panel自身にLayoutGroupを付けると Header/FooterNote の位置がLayoutGroupに上書きされる

OK（階層を分離）:
Panel（アンカー固定のみ。LayoutGroupを持たない）
├── Header        … アンカーで左上固定
├── ButtonRowRoot  … アンカーで中央固定。この配下にのみHorizontalLayoutGroupを持つ
│   └── ButtonRow  … HorizontalLayoutGroup（Button×n）
└── FooterNote    … アンカーで下端固定
```

## ContentSizeFitterの正しい付与範囲

**不変条件4**：LayoutGroupの子に`ContentSizeFitter`を付与しない。子の寸法は`LayoutElement`で与える。

`ContentSizeFitter`は「このオブジェクト自身の`RectTransform`を、レイアウト計算結果（子の内容）に合わせて自動的に伸縮させる」コンポーネントである。付与先を誤ると、親のLayoutGroupと子のContentSizeFitterが互いのサイズ計算を待ち合ってレイアウトが安定しない、または毎フレーム再計算が走るという典型的な不具合になる。

### 付与してよい対象

- LayoutGroup（`HorizontalLayoutGroup`／`VerticalLayoutGroup`／`GridLayoutGroup`）**を持つオブジェクト自身**。例：ScrollRectのContent（[ScrollRectのレイアウト構成](#scrollrectのレイアウト構成)）。
- 子の内容量に応じてパネル自体を伸縮させたい、かつそのパネルがさらに親のLayoutGroupの子になっていない（＝伸縮した結果を誰も再計算する必要がない）場合。

### 付与してはいけない対象

- LayoutGroupの**子**（`HorizontalLayoutGroup`／`VerticalLayoutGroup`／`GridLayoutGroup`配下の各要素）。寸法は`LayoutElement`で与える。
- ScrollRectのViewport（`RectMask2D`のみを持ち、`ContentSizeFitter`は持たない。`UiFactory.CreateScrollRect`のViewport生成箇所を参照）。

```csharp
// NG：VerticalLayoutGroupの子にContentSizeFitterを付与している。
var rowGo = new GameObject("Row", typeof(RectTransform), typeof(ContentSizeFitter)); // 不変条件4違反
rowGo.transform.SetParent(contentWithVerticalLayoutGroup, false);

// OK：子の寸法はLayoutElementで与える。ContentSizeFitterはContent自身にのみ存在する。
var rowGo = new GameObject("Row", typeof(RectTransform), typeof(LayoutElement));
rowGo.transform.SetParent(contentWithVerticalLayoutGroup, false);
rowGo.GetComponent<LayoutElement>().preferredHeight = UiTheme.Sizes.TapMinSize;
```

## ScrollRectのレイアウト構成

**不変条件5**：ScrollRectはViewport（`RectMask2D`）とContent（LayoutGroup＋`ContentSizeFitter`）の構成で組む。

構成は固定で以下の3階層である（`UiFactory.CreateScrollRect`が参照実装）。

```
ScrollRect（ScrollRectコンポーネント本体。全体に対してStretchFull）
└── Viewport（RectMask2Dのみ。ContentSizeFitterは持たない。StretchFull）
    └── Content（VerticalLayoutGroup + ContentSizeFitter を自身に持つ）
        ├── Row1（LayoutElementで寸法指定。ContentSizeFitterは持たない）
        ├── Row2（同上）
        └── ...
```

- **Viewport**：`RectMask2D`でクリッピングするだけの層。可視背景を持つ場合も`Image.color`は`Color.clear`とし、装飾ではなくマスク描画のために存在する（`UiFactory`のコメントを参照）。
- **Content**：`VerticalLayoutGroup`（横スクロール一覧なら`HorizontalLayoutGroup`）と`ContentSizeFitter`を自身に持つ。`ContentSizeFitter`は伸縮させたい軸（一覧の伸びる方向）を`PreferredSize`、固定したい軸を`Unconstrained`にする。縦一覧なら`verticalFit = PreferredSize`・`horizontalFit = Unconstrained`が典型。
- **行（Row）**：Content配下の各要素。`ContentSizeFitter`は持たず、`LayoutElement`で高さ（縦一覧の場合）を与える。

### 50件超・件数不明の一覧

件数が不明または50件を超える場合は、行オブジェクトを都度生成・破棄せず、可視範囲分だけ生成して使い回す（プール）設計をF3で検討する（`SKILL.md`「F3：コード構造設計」手順4）。プール設計の詳細・スクロール性能の指針は`references/webgl-runtime.md`（一覧が50件を超えるとき）を参照する。本ファイルはレイアウト構成の正しさまでを扱う。

## 追従規則（CanvasScaler）

F2手順7（`SKILL.md`）で定めた追従規則をレイアウト実装の観点から補足する。

- `CanvasScaler.uiScaleMode`は`ScaleMode.ScaleWithScreenSize`に固定する（不変条件3）。
- `referenceResolution`は前提セット（F1）で決まった値を使う。未指定時の既定は1920×1080。
- `screenMatchMode`は`MatchWidthOrHeight`とし、`matchWidthOrHeight`は**横長画面で0.5・縦長画面で0**（幅基準）とする。値の根拠：縦長（アスペクト比1未満、スマートフォン縦持ち等）では横幅の取りこぼしがタップ領域の圧迫に直結するため幅基準（0）を優先し、横長では高さ・幅どちらかに偏らせず折衷（0.5）する。
- 縦横どちらを基準にするかを実行時に切り替える場合は、`Screen.width`と`Screen.height`の比較で判定し、`UiTheme`に集約した閾値・既定値以外のリテラルを増やさない。

```csharp
// 縦長・横長でmatchWidthOrHeightを切り替える例（UiFactory.CreateCanvasの呼び出し側）。
var isPortrait = Screen.height > Screen.width;
var matchWidthOrHeight = isPortrait ? 0f : 0.5f;
var canvasRefs = UiFactory.CreateCanvas("MainCanvas", referenceResolution, matchWidthOrHeight, sortingOrder: 0);
```

### 端寄せ・中央コンテンツとの関係

[アンカーとピボットの使い方](#アンカーとピボットの使い方)で述べた通り、端に寄せる要素はアンカーで、中央の内容は最大幅を持つコンテナで制御する。`matchWidthOrHeight`の値を変えても、アンカーで端固定した要素は追従し、中央コンテナは`LayoutElement.preferredWidth`の上限で頭打ちになるため、超横長・超縦長でも崩れない。追従規則とレイアウト方式（アンカー／LayoutGroup／ScrollRect）は独立した設計判断ではなく、常に組み合わせて検討する。

## レイアウト崩れの診断手順（改修モード）

既存画面のレイアウト崩れを改修する際は、次の順で原因を切り分ける（`SKILL.md`「F0」〜「F3」の改修モード手順に沿う）。

1. **階層混在の確認**：崩れている親の直接の子に、アンカー固定を意図したものとLayoutGroup前提のものが同居していないか（[同一階層でアンカー固定とLayoutGroupを混在させない](#同一階層でアンカー固定とlayoutgroupを混在させない)）。
2. **ContentSizeFitterの付与先の確認**：LayoutGroupの子に`ContentSizeFitter`が付いていないか（不変条件4）。付いていれば、子の寸法指定を`LayoutElement`に置き換え、`ContentSizeFitter`は削除する。
3. **ScrollRect構成の確認**：Viewportに`ContentSizeFitter`が付いていないか、Contentに`RectMask2D`が付いていないか（構成の入れ替わり）。不変条件5の3階層構成と照合する。
4. **ピボットとアンカーの不一致の確認**：`anchoredPosition`で動かしているのに`pivot`がアンカーの基準点と一致していないケースがないか。
5. **追従規則の確認**：`CanvasScaler`が`ScaleWithScreenSize`になっているか、`matchWidthOrHeight`が画面の縦横比に対して不適切な値になっていないか。
6. 上記いずれにも該当しない場合のみ、個別の`RectTransform`の数値（`sizeDelta`・`offsetMin`/`offsetMax`）を疑う。

改修モードでは、要求範囲外の階層まで踏み込んで直さない（不変条件11）。上記診断で範囲外の崩れを見つけた場合は、修正せず所見として報告する。

## アンチパターン早見表

| アンチパターン | 何が起きるか | 対処 |
|---|---|---|
| LayoutGroupの子に`ContentSizeFitter`を付与 | 親子でサイズ計算が循環し、レイアウトが安定しない（不変条件4違反） | 子は`LayoutElement`で寸法指定に置き換える |
| ScrollRectのViewportに`ContentSizeFitter`を付与 | Viewportがクリッピング領域として機能しなくなる | Viewportは`RectMask2D`のみ。伸縮はContent側で行う |
| 同一階層でアンカー固定とLayoutGroupを混在 | LayoutGroupがアンカー固定の子の位置・寸法を上書きする | 固定したい子を別階層（LayoutGroup外）へ分離する |
| ピボットとアンカーの基準点が不一致のまま`anchoredPosition`を使用 | 解像度・スケール変化時に位置がずれる | ピボットをアンカーの`min`/`max`と揃える |
| 色・寸法・文字サイズをリテラルで直書き | テーマ変更時に画面ごとに直す必要が生じる（不変条件9違反） | `UiTheme.Colors`／`UiTheme.Sizes`／`UiTheme.TextSizes`を参照する |
| `matchWidthOrHeight`を画面の縦横比によらず固定値にする | 超縦長・超横長で要素がはみ出す、または間延びする | 横長0.5・縦長0を基準に、判定を`UiTheme`集約の閾値で行う |
| 中央コンテンツをストレッチのみで広げる | 超横長画面で行が間延びし可読性が落ちる | 最大幅を持つコンテナ（`LayoutElement.preferredWidth`）で頭打ちにする |
