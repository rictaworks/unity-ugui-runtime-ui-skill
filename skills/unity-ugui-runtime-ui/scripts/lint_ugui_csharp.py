#!/usr/bin/env python3
"""uGUI ランタイムUI C# の禁止パターン・必須構成を検査する静的リンタ。

requirements.md 7.3節末尾に定義された8種の禁止パターンを検査する：

1. ``UnityEditor`` 名前空間の参照
2. ``OnGUI`` 定義
3. ``AssetDatabase`` ・ ``GetBuiltinExtraResource`` の使用
4. ``GameObject.Find`` ・ ``transform.Find`` による生成後の再取得
5. LayoutGroup配下への ``ContentSizeFitter`` 付与
6. ``EventSystem`` 生成の欠落
7. ``CanvasScaler`` 設定の欠落
8. テーマ外の色リテラル（``new Color(...)`` の直書き・ ``Color.red`` 等）

Python 3標準ライブラリのみで動作する（追加パッケージ不要）。

使い方::

    python3 lint_ugui_csharp.py <path> [<path> ...]

``<path>`` にはファイルまたはディレクトリを指定できる。ディレクトリを指定した
場合は配下の ``*.cs`` を再帰的に走査する。違反が1件でもあれば非ゼロの終了コード
を返す。

コンポーネント付与の検出について：``AddComponent<T>()`` 方式と
``new GameObject(name, typeof(T), ...)`` コンストラクタ列挙方式の両方を検出対象と
する（後者は同一行内での判定に限る。複数行にまたがるコンストラクタ呼び出しは
検出できない）。親子付けの検出も同様に ``x.transform.SetParent(...)`` と
``x.SetParent(...)``（RectTransform変数への直接呼び出し）の両方を対象とする。

コメントの扱いについて：各行の ``//`` 以降（単一行コメント）は、走査前に一律で
除去してから正規表現マッチを行う。これにより日本語コメント中の
``UnityEditor``・``AssetDatabase`` 等の語を誤検出しない。ただし文字列リテラル内
に ``//`` が含まれる場合も同様に除去してしまう簡易実装であり、C# の文字列リテラ
ルまでは解析しない（既知の制限）。複数行コメント（``/* */``）は対象外。

注意（既知の制限）：正規表現ベースの単純な検査であり、文字列リテラル内の記述や
コンパイラのプリプロセッサディレクティブは考慮しない。複数行にまたがる式
（例：複数行の ``new Color(...)`` 呼び出しや複数行の ``new GameObject(...)``
コンストラクタ呼び出し）は検出できない場合がある。
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class Violation:
    """1件の違反を表す。"""

    file_path: str
    line_number: int  # 特定の行に紐付かない場合は 0
    rule_id: str
    message: str


# ---------------------------------------------------------------------------
# 行単位の正規表現で検出できる禁止パターン（1〜4, 8）
# ---------------------------------------------------------------------------

_RULES: Tuple[Tuple[str, "re.Pattern[str]", str], ...] = (
    (
        "unity_editor_namespace",
        re.compile(r"\bUnityEditor\b"),
        "UnityEditor 名前空間を実行時コードに含めない（Editor拡張は Assets/Editor/ の"
        "CLI実行用に限る）",
    ),
    (
        "ongui_definition",
        re.compile(r"\bOnGUI\s*\("),
        "OnGUI の定義は実行時コードに含めない（IMGUI は対象外）",
    ),
    (
        "asset_database_usage",
        re.compile(r"\bAssetDatabase\b|\bGetBuiltinExtraResource\b"),
        "AssetDatabase・GetBuiltinExtraResource の使用は実行時コードで禁止。"
        "実行時生成の9分割スプライト等で代替する",
    ),
    (
        "find_reacquisition",
        re.compile(r"\bGameObject\.Find\s*\(|\btransform\.Find\s*\("),
        "GameObject.Find・transform.Find による生成後の再取得は禁止。生成時の"
        "参照をフィールドで保持する",
    ),
    (
        "raw_color_literal",
        re.compile(
            r"\bnew\s+Color(32)?\s*\("
            r"|\bColor\.(red|green|blue|white|black|yellow|cyan|magenta|gray|grey)\b"
        ),
        "テーマ外の色リテラル。色は UiTheme（または定数）に集約する。"
        "ただし Color.clear（透明色。マスク描画等で用いる構造上の値であり配色では"
        "ないため対象外）、UiTheme クラス自身の色定数定義（集約先そのもの）、"
        "既存Colorの成分（.r/.g/.b/.a）から派生させた値（例：同色で不透明度のみ"
        "変えた new Color32(c.r, c.g, c.b, 0)）は除く",
    ),
)

# raw_color_literal専用：new Color(32)?(...) の引数に既存Colorの成分アクセス
# （.r/.g/.b/.a）が含まれる場合、新規の色リテラル導入ではなく既存色からの派生
# （例：CreateNineSliceSpriteの `new Color32(fillColor.r, fillColor.g, fillColor.b, 0)`）
# とみなして除外する。
_COLOR_COMPONENT_ACCESS_RE = re.compile(r"\.(r|g|b|a)\b")

# ---------------------------------------------------------------------------
# パターン5：LayoutGroup配下へのContentSizeFitter付与
#
# AddComponent<T>() 方式に加え、new GameObject(name, typeof(RectTransform),
# typeof(T), ...) というコンストラクタ列挙方式でのコンポーネント付与も検出する。
# 後者は「変数 = new GameObject(...)」の行に対象の typeof(...) が同一行内に
# 含まれるかどうかで判定する（複数行にまたがる呼び出しは対象外）。
# ---------------------------------------------------------------------------

_LAYOUT_GROUP_ADD_RE = re.compile(r"\b(\w+)\.AddComponent<\w*LayoutGroup>\s*\(")
_CONTENT_SIZE_FITTER_ADD_RE = re.compile(r"\b(\w+)\.AddComponent<ContentSizeFitter>\s*\(")
_SET_PARENT_RE = re.compile(r"\b(\w+)\.(?:transform\.)?SetParent\s*\(\s*(\w+)")

_NEW_GAMEOBJECT_ASSIGN_RE = re.compile(r"\b(\w+)\s*=\s*new\s+GameObject\s*\(")
_TYPEOF_LAYOUT_GROUP_RE = re.compile(r"\btypeof\s*\(\s*\w*LayoutGroup\s*\)")
_TYPEOF_CONTENT_SIZE_FITTER_RE = re.compile(r"\btypeof\s*\(\s*ContentSizeFitter\s*\)")

# ---------------------------------------------------------------------------
# パターン6・7：EventSystem生成の欠落／CanvasScaler設定の欠落
#
# こちらも AddComponent<T>() 方式と typeof(T) コンストラクタ列挙方式の両方を
# 1つの正規表現の選択(|)で検出する。
# ---------------------------------------------------------------------------

_CANVAS_ADD_RE = re.compile(r"\bAddComponent<Canvas>\s*\(|\btypeof\s*\(\s*Canvas\s*\)")
_CANVAS_SCALER_ADD_RE = re.compile(
    r"\bAddComponent<CanvasScaler>\s*\(|\btypeof\s*\(\s*CanvasScaler\s*\)"
)
_EVENT_SYSTEM_ADD_RE = re.compile(
    r"\bAddComponent<EventSystem>\s*\(|\btypeof\s*\(\s*EventSystem\s*\)"
)


def _strip_line_comments(content: str) -> str:
    """各行の ``//`` 以降（単一行コメント）を除去した文字列を返す。

    素朴な実装であり、文字列リテラル中に ``//`` が含まれる場合もそこで切り詰めて
    しまう（C# の文字列リテラルの構文解析は行わない）。本リンタが検査する生成
    コードは URL 等を文字列リテラルとして持たない前提のため、既知の制限として
    許容する。行数（改行の数）は変えないため、行番号の対応は保たれる。
    """
    stripped_lines = []
    for line in content.splitlines():
        idx = line.find("//")
        stripped_lines.append(line[:idx] if idx != -1 else line)
    return "\n".join(stripped_lines)


def _find_all_with_lines(
    pattern: "re.Pattern[str]", content: str
) -> List[Tuple[int, "re.Match[str]"]]:
    """行番号付きで正規表現の全マッチを返す。"""
    results: List[Tuple[int, "re.Match[str]"]] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for m in pattern.finditer(line):
            results.append((line_no, m))
    return results


def _find_typeof_component_receivers(
    content: str, typeof_pattern: "re.Pattern[str]"
) -> List[Tuple[int, str]]:
    """``変数 = new GameObject(..., typeof(X), ...)`` 形式で該当コンポーネントが
    付与された行番号と受け手の変数名の一覧を返す。

    同一行内に代入とtypeof(...)が両方存在するかで判定する簡易実装であり、
    複数行にまたがるコンストラクタ呼び出しは検出できない。
    """
    results: List[Tuple[int, str]] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        assign_match = _NEW_GAMEOBJECT_ASSIGN_RE.search(line)
        if assign_match and typeof_pattern.search(line):
            results.append((line_no, assign_match.group(1)))
    return results


def _find_class_body_line_ranges(content: str, class_name: str) -> List[Tuple[int, int]]:
    """``class <class_name>``（完全一致・単語境界）の宣言に続くクラス本体の
    開始・終了行番号（両端含む）のリストを返す。

    波括弧の対応をその場で数える単純な走査であり、正規表現のバックトラッキング
    に依存しないため線形時間で終わる（ReDoSのリスクなし）。ネストしたクラス・
    メソッドの波括弧も同じカウンタで数えるため、対象クラスの本体全体（ネストし
    た静的クラスを含む）が範囲に含まれる。
    """
    ranges: List[Tuple[int, int]] = []
    pattern = re.compile(rf"\bclass\s+{re.escape(class_name)}\b")
    for m in pattern.finditer(content):
        brace_start = content.find("{", m.end())
        if brace_start == -1:
            continue
        depth = 0
        end_idx = None
        idx = brace_start
        while idx < len(content):
            ch = content[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end_idx = idx
                    break
            idx += 1
        if end_idx is None:
            continue
        start_line = content.count("\n", 0, brace_start) + 1
        end_line = content.count("\n", 0, end_idx) + 1
        ranges.append((start_line, end_line))
    return ranges


def _line_in_ranges(line_no: int, ranges: Sequence[Tuple[int, int]]) -> bool:
    return any(start <= line_no <= end for start, end in ranges)


def check_simple_patterns(file_path: str, content: str) -> List[Violation]:
    """行単位の正規表現で検出できる禁止パターン（1〜4, 8）を検査する。"""
    violations: List[Violation] = []
    # UiTheme（色・寸法・文字サイズ・文言の集約先）自身のクラス本体内で定義される
    # 色定数は raw_color_literal の対象外とする（過度な除外を避けるため、対象は
    # クラス名 UiTheme の本体内に限定する）。
    uitheme_ranges = _find_class_body_line_ranges(content, "UiTheme")
    lines = content.splitlines()
    for rule_id, pattern, message in _RULES:
        for line_no, match in _find_all_with_lines(pattern, content):
            if rule_id == "raw_color_literal":
                if _line_in_ranges(line_no, uitheme_ranges):
                    continue
                matched_text = match.group(0).lstrip()
                if matched_text.startswith("new") and _COLOR_COMPONENT_ACCESS_RE.search(
                    lines[line_no - 1]
                ):
                    # new Color(32)?(...) の引数が既存Colorの成分（.r/.g/.b/.a）
                    # から派生した値である場合、新規の色リテラル導入とはみなさない。
                    continue
            violations.append(Violation(file_path, line_no, rule_id, message))
    return violations


def check_layout_group_child_content_size_fitter(
    file_path: str, content: str
) -> List[Violation]:
    """LayoutGroupを持つオブジェクトの子に ContentSizeFitter が付与されていないか検査する。

    ScrollRectのContent自身（LayoutGroupとContentSizeFitterを同一オブジェクトに
    付与する構成）は許容し、SetParentで別オブジェクトの子になった上で
    ContentSizeFitterが付与されている場合のみ違反とする。

    コンポーネント付与は AddComponent<T>() 方式・typeof(T) コンストラクタ列挙
    方式のどちらでも検出する。
    """
    layout_lines = _find_all_with_lines(_LAYOUT_GROUP_ADD_RE, content)
    layout_receivers = {m.group(1) for _, m in layout_lines}
    layout_receivers.update(
        name for _, name in _find_typeof_component_receivers(content, _TYPEOF_LAYOUT_GROUP_RE)
    )

    parent_of: dict[str, str] = {}
    for _, m in _find_all_with_lines(_SET_PARENT_RE, content):
        child, parent = m.group(1), m.group(2)
        parent_of.setdefault(child, parent)

    content_size_fitter_receivers: List[Tuple[int, str]] = [
        (line_no, m.group(1))
        for line_no, m in _find_all_with_lines(_CONTENT_SIZE_FITTER_ADD_RE, content)
    ]
    content_size_fitter_receivers.extend(
        _find_typeof_component_receivers(content, _TYPEOF_CONTENT_SIZE_FITTER_RE)
    )

    violations: List[Violation] = []
    for line_no, receiver in content_size_fitter_receivers:
        if receiver in layout_receivers:
            # LayoutGroupを持つオブジェクト自身への付与（ScrollRectのContent等）は許容
            continue
        parent = parent_of.get(receiver)
        if parent is not None and parent in layout_receivers:
            violations.append(
                Violation(
                    file_path,
                    line_no,
                    "layout_group_child_content_size_fitter",
                    f"LayoutGroup を持つ '{parent}' の子 '{receiver}' に "
                    "ContentSizeFitter を付与している。子の寸法は LayoutElement で与える",
                )
            )
    return violations


def check_canvas_scaler_missing(file_path: str, content: str) -> List[Violation]:
    """Canvasを生成しているにも関わらずCanvasScalerが同一ファイルに無い場合を検査する。"""
    canvas_matches = _find_all_with_lines(_CANVAS_ADD_RE, content)
    if not canvas_matches:
        return []
    if _CANVAS_SCALER_ADD_RE.search(content):
        return []
    line_no = canvas_matches[0][0]
    return [
        Violation(
            file_path,
            line_no,
            "canvas_scaler_missing",
            "Canvas に CanvasScaler（ScaleWithScreenSize）が付与されていない",
        )
    ]


def check_event_system_missing(
    files_content: Sequence[Tuple[str, str]]
) -> List[Violation]:
    """走査対象全体でCanvas生成があるのにEventSystem生成が1つも無い場合を検査する。

    EventSystemはシーンに1つのみ生成すればよく、Canvasを生成する個々の画面ファイル
    に必須ではないため、走査対象全体（複数ファイル）を対象に判定する。
    """
    canvas_files = [
        (path, content)
        for path, content in files_content
        if _CANVAS_ADD_RE.search(content)
    ]
    if not canvas_files:
        return []
    has_event_system_anywhere = any(
        _EVENT_SYSTEM_ADD_RE.search(content) for _, content in files_content
    )
    if has_event_system_anywhere:
        return []
    violations: List[Violation] = []
    for path, content in canvas_files:
        line_no = _find_all_with_lines(_CANVAS_ADD_RE, content)[0][0]
        violations.append(
            Violation(
                path,
                line_no,
                "event_system_missing",
                "Canvas を生成しているが EventSystem の生成が見つからない。"
                "シーンに1つ生成する",
            )
        )
    return violations


def _collect_cs_files(paths: Iterable[str]) -> List[str]:
    files: List[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for name in names:
                    if name.endswith(".cs"):
                        files.append(os.path.join(root, name))
        elif p.endswith(".cs"):
            files.append(p)
    return sorted(files)


def lint_paths(paths: Iterable[str]) -> List[Violation]:
    """指定パス（ファイル・ディレクトリ）配下の .cs を検査し、違反一覧を返す。"""
    files = _collect_cs_files(paths)
    files_content: List[Tuple[str, str]] = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            raw = fh.read()
        # 単一行コメント（//以降）を先に除去してから以降のすべての検査にかける。
        files_content.append((f, _strip_line_comments(raw)))

    violations: List[Violation] = []
    for path, content in files_content:
        violations.extend(check_simple_patterns(path, content))
        violations.extend(
            check_layout_group_child_content_size_fitter(path, content)
        )
        violations.extend(check_canvas_scaler_missing(path, content))
    violations.extend(check_event_system_missing(files_content))
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="uGUI ランタイムUI C# の禁止パターン・必須構成を検査する"
    )
    parser.add_argument(
        "path", nargs="+", help="検査対象の .cs ファイルまたはディレクトリ"
    )
    args = parser.parse_args(argv)

    violations = lint_paths(args.path)
    violations.sort(key=lambda v: (v.file_path, v.line_number, v.rule_id))

    for v in violations:
        location = f"{v.file_path}:{v.line_number}" if v.line_number else v.file_path
        print(f"{location}: [{v.rule_id}] {v.message}")

    if violations:
        print(f"{len(violations)} 件の違反が見つかりました", file=sys.stderr)
        return 1

    print("違反は見つかりませんでした")
    return 0


if __name__ == "__main__":
    sys.exit(main())
