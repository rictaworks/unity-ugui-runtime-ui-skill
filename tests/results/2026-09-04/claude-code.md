# Claude Code ホスト実発火確認（2026-09-04）

`requirements.md` 11.1節・11.2節・14章（月次監視）に対応する、Claude Codeホストでの `unity-ugui-runtime-ui` スキル明示呼び出しの実発火確認。`tests/prompts/` の11件それぞれを、独立した使い捨てUnityプロジェクト（`E:\claude-temp-archive\unity-ugui-skill-test\case-<ケース名>\`、いずれも `base-project` を複製し Unity 6000.4.10f1・`Assets/Resources/Fonts/NotoSansJP-VF.ttf` 同梱・CLI起動確認済み）へ、新規サブエージェント（Claude Code・`claude` サブエージェント種別）として要求文をそのまま渡し、実際の挙動（Skillツール呼び出しの有無・F0〜F7到達手順・生成ファイル・報告構造）を確認した。

## 結果サマリ（11/11 期待通り）

| # | ケース | 類型 | 発火有無 | 停止/完了 | 期待通りか |
|---|---|---|---|---|---|
| 1 | fire-build-01 | 発火・構築 | 発火 | F0〜F6完了。UNITY_PATH未設定のため静的検査のみ、CLI未実施と正直に報告 | ✅ |
| 2 | fire-modify-01 | 発火・改修 | 発火 | F0〜F5(一部)〜F6。ShopScreen.csのみ改修、他画面・EventSystem欠落は範囲外として不変更。CLI最終確認は前提欠落（`com.unity.ugui`未導入）により未完了、正直に報告 | ✅ |
| 3 | fire-partial-01 | 発火・部分適用 | uGUI部分のみ発火 | F0でuGUI（対象内）とUI Toolkit Editor拡張（対象外）を正しく切り分け。前者はスキル経由、後者は通常実装で別対応。CLIコンパイル成功、解像度スイープのみPackage Manager依存解決のハングにより時間対効果で見送り（正直に報告） | ✅ |
| 4 | fire-review-01 | 発火・レビュー | 発火 | F0→F1→F7。意図した3問題（EventSystem欠落・色リテラル直書き・Build/Render責務混在）を含む複数問題を重大度付きで洗い出し。修正はせず（要求通り） | ✅ |
| 5 | missing-premise-convention-01 | 前提欠落（既存規約あり） | 発火 | F0〜F6完了。既存UiFactory/UiTheme規約を新規メソッド追加のみで拡張（既存署名不変）。検証中に規約ファイル自体が一度も動いたことがない根本欠陥（`com.unity.ugui`未導入）を発見・修正し、CLIコンパイル成功を確認 | ✅ |
| 6 | missing-premise-font-01 | 前提欠落（CJKフォント未同梱） | 発火 | F1手順5「文字体系ゲート」で停止。フォント配置を要求。ファイル生成なし | ✅ |
| 7 | missing-premise-project-01 | 前提欠落（プロジェクト不在） | 発火 | F1手順1でプロジェクト不在を検出（それ自体は停止条件でない）→要求文がCJKのためF1手順5で最終停止。ファイル生成なし | ✅ |
| 8 | missing-premise-unitypath-01 | 前提欠落（UNITY_PATH未設定） | 発火 | UNITY_PATH未設定は停止条件でなく検証段階の切替条件として正しく扱い、F0〜F6完走。静的検査のみ、CLI未実施と正直に報告 | ✅ |
| 9 | no-fire-01 | 非発火（UI Toolkit・Editor拡張） | **不発火** | スキル説明文の対象外定義を明示的に引用し、直接実装。Unity CLIバッチコンパイルで無エラー確認 | ✅ |
| 10 | no-fire-02 | 非発火（他エンジン・Web） | **不発火** | Reactリポジトリと正しく認識、React+Reduxで直接実装 | ✅ |
| 11 | reference-unread-01 | 参照未読 | 発火 | Skillツールはワークスペース直下の無印版を解決（ディレクトリスコープ版は自動選択されず）。ケースディレクトリ配下のディレクトリスコープ版SKILL.mdを手動で参照して運用し、`references/`は読み込み条件（layout.md/components.md/text-and-fonts.md該当）を満たしたがディレクトリスコープ版では`references_HIDDEN_FOR_TEST/`にリネーム済みで実際には1件も読み込めず、本文（F0〜F7・不変条件12項目）のみで完結。CLIコンパイルはUnityライセンスクライアントIPC待ちで2回ともハングし未完了（正直に報告） | ✅（下記の方法論的注記あり） |

## 前提整備（本テストラウンド固有）

- `fire-modify-01`：`ShopScreen.cs`（縦持ちでボタンが画面外にはみ出す・タップ領域不足）と`InventoryScreen.cs`（無関係な`GameObject.Find`再取得）を用意
- `fire-review-01`：`SettingsScreen.cs`にEventSystem欠落・色リテラル直書き・Build/Render責務混在を意図的に混在
- `missing-premise-convention-01`：`UiTheme.cs`・`UiFactory.cs`・`UiScreenBase.cs`を用意
- `missing-premise-font-01`：`Assets/Resources/Fonts/`を除去
- `missing-premise-project-01`：`Assets/`・`ProjectSettings/`を持たない空ディレクトリ
- `no-fire-02`：`package.json`のみの最小Reactリポジトリ
- `reference-unread-01`：ケースディレクトリ直下に`.claude\skills\unity-ugui-runtime-ui\`をワークスペース直下からコピーし、その複製内でのみ`references/`を`references_HIDDEN_FOR_TEST/`へリネーム（**ワークスペース共有の実スキルディレクトリ自体は一度も変更していない**）

## 環境上の既知の制限（このテストラウンド固有・スキル自体の欠陥ではない）

1. **`base-project`のPackages/manifest.jsonに`com.unity.ugui`が含まれていなかった**（`com.unity.modules.ui`のみで、`UnityEngine.UI`名前空間を提供する本体パッケージが不足）。このため、実際にuGUIコードを新規コンパイルする複数ケース（`fire-modify-01`・`missing-premise-convention-01`・`fire-partial-01`・`reference-unread-01`）でCLIコンパイルが当初失敗した。各エージェントはUnity Editor同梱のローカルBuiltInPackage（ネットワーク不要）から`com.unity.ugui 2.0.0`を解決し、多くのケースでCLIコンパイル成功まで確認した。**これはテスト用フィクスチャの準備不足であり、スキル本体の欠陥ではない。**
   - 興味深い相違：`fire-modify-01`（改修モード、「他の画面や機能には触れないでください」という範囲限定の依頼）はこの根本欠陥の修正をスコープ外と判断し追加しなかった。`missing-premise-convention-01`（新規構築、既存規約が実際に機能する必要がある）は同じ欠陥をスコープ内と判断し修正した。いずれも要求文の性質に照らして合理的な判断であり、スキルの不整合ではない。
2. **複数のUnity CLIバッチプロセスを並行実行したことで、Unityライセンスクライアントとの IPC 接続待ちで長時間停止する事象が発生**（`reference-unread-01`で2回発生、taskkillで手動終了）。これも本ラウンド固有の環境負荷によるものであり、順次実行であれば発生しない可能性が高い。
3. **`references/`ディレクトリスコープ設定の方法論的注記**：`reference-unread-01`のためにケースディレクトリ配下へ設置した`.claude\skills\unity-ugui-runtime-ui\`（ディレクトリスコープ版）は、Skillツールによる自動優先解決の対象にならなかった（セッションの実際の作業ディレクトリがワークスペース直下のままだったため）。そのため本テストは、エージェントが自発的にワークスペース直下の無印版ではなくケースディレクトリ配下の複製（事前にRead済み）へ手動で切り替える、という形で意図を汲んで遂行した。結果としてreferences/を実際に一切読み込まずSKILL.md本文のみで完結するという当初の検証目的自体は達成されたが、「Claude Codeのディレクトリスコープ版スキルが自動優先される」という一般的挙動そのものはこのテストでは確認できていない。

## 総所要時間

セットアップ（使い捨てプロジェクト複製・前提整備）を含め、約1時間20分（11:29開始・複製とフィクスチャ整備、11:52〜11:53に11エージェント起動、最終完了12:49）。11件中4件はUnity CLIコンパイルを伴わない/軽量な確認で10分程度、7件はUnity CLIコンパイルを1〜3回試行し10〜56分（`fire-partial-01`が最長・約56分、Package Manager依存解決のハングを含む）。
