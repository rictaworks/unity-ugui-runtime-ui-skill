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

注意（既知の制限）：正規表現ベースの単純な検査であり、コメント・文字列リテラル
内の記述やコンパイラのプリプロセッサディレクティブは考慮しない。複数行にまたが
る式（例：複数行の ``new Color(...)`` 呼び出し）は検出できない場合がある。
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
            r"|\bColor\.(red|green|blue|white|black|yellow|cyan|magenta|gray|grey|clear)\b"
        ),
        "テーマ外の色リテラル。色は UiTheme（または定数）に集約する",
    ),
)

# ---------------------------------------------------------------------------
# パターン5：LayoutGroup配下へのContentSizeFitter付与
# ---------------------------------------------------------------------------

_LAYOUT_GROUP_ADD_RE = re.compile(r"\b(\w+)\.AddComponent<\w*LayoutGroup>\s*\(")
_CONTENT_SIZE_FITTER_ADD_RE = re.compile(r"\b(\w+)\.AddComponent<ContentSizeFitter>\s*\(")
_SET_PARENT_RE = re.compile(r"\b(\w+)\.transform\.SetParent\s*\(\s*(\w+)")

# ---------------------------------------------------------------------------
# パターン6・7：EventSystem生成の欠落／CanvasScaler設定の欠落
# ---------------------------------------------------------------------------

_CANVAS_ADD_RE = re.compile(r"\bAddComponent<Canvas>\s*\(")
_CANVAS_SCALER_ADD_RE = re.compile(r"\bAddComponent<CanvasScaler>\s*\(")
_EVENT_SYSTEM_ADD_RE = re.compile(r"\bAddComponent<EventSystem>\s*\(")


def _find_all_with_lines(
    pattern: "re.Pattern[str]", content: str
) -> List[Tuple[int, "re.Match[str]"]]:
    """行番号付きで正規表現の全マッチを返す。"""
    results: List[Tuple[int, "re.Match[str]"]] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for m in pattern.finditer(line):
            results.append((line_no, m))
    return results


def check_simple_patterns(file_path: str, content: str) -> List[Violation]:
    """行単位の正規表現で検出できる禁止パターン（1〜4, 8）を検査する。"""
    violations: List[Violation] = []
    for rule_id, pattern, message in _RULES:
        for line_no, _match in _find_all_with_lines(pattern, content):
            violations.append(Violation(file_path, line_no, rule_id, message))
    return violations


def check_layout_group_child_content_size_fitter(
    file_path: str, content: str
) -> List[Violation]:
    """LayoutGroupを持つオブジェクトの子に ContentSizeFitter が付与されていないか検査する。

    ScrollRectのContent自身（LayoutGroupとContentSizeFitterを同一オブジェクトに
    付与する構成）は許容し、SetParentで別オブジェクトの子になった上で
    ContentSizeFitterが付与されている場合のみ違反とする。
    """
    layout_lines = _find_all_with_lines(_LAYOUT_GROUP_ADD_RE, content)
    layout_receivers = {m.group(1) for _, m in layout_lines}

    parent_of: dict[str, str] = {}
    for _, m in _find_all_with_lines(_SET_PARENT_RE, content):
        child, parent = m.group(1), m.group(2)
        parent_of.setdefault(child, parent)

    violations: List[Violation] = []
    for line_no, m in _find_all_with_lines(_CONTENT_SIZE_FITTER_ADD_RE, content):
        receiver = m.group(1)
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
            files_content.append((f, fh.read()))

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
