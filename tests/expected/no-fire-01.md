# 期待結果：非発火（no-fire-01）

対応プロンプト：`tests/prompts/no-fire-01.md`

## 発火可否

**発火しない。または発火直後にF0で取り下げる。**

- 要求文は「UI Toolkit（UXML/USS）」「Editor拡張」「EditorWindow」のみで構成され、`description`が明示的に除外する文脈（「UI Toolkit（UXML/USS）、EditorWindow・IMGUI…には使わない」）に完全に一致する。3.3節「発火すべきでない要求の類型」の「UI ToolkitでのUI構築」「Editor拡張・Inspector拡張・IMGUI」の2つに該当する。
- uGUI・Canvas・RectTransform・ScrollRect・Button等、発火語（3.1節）に該当する語を一切含まない。

## モード判定（F0）

該当なし。仮に発火判定に入った場合でも、F0手順1で「uGUIでコードから作る・直す・見る」に該当する部分が空と判定され、F0手順2により**適用を取り下げる**。取り下げの応答は「範囲外である旨と代替（UI Toolkit・Editor拡張は本スキルの範囲外）」を1文で示すのみで終了する。

## 停止可否

停止（＝スキルとして処理を進めない）という意味では該当するが、これはF1の「文字体系ゲート」等の停止条件ではなく、F0での適用取り下げである。

## 期待される報告構造

`assets/report-template.md`の7見出し構造は**出力されない**。取り下げの1文のみで完結する。

## 生成ファイル名（期待）

なし。
