#!/usr/bin/env python3
"""CI検証スクリプト群が共有するユーティリティ。

Python 3標準ライブラリのみで動作する（PyYAML等の追加パッケージに依存しない）。
requirements.md 7.1節の構成（`skills/<skill-name>/SKILL.md`）を前提とする。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"

# Agent Skills標準で共通なのは name・description・本文のコアのみ（requirements.md 1.5節）。
# metadata はバージョン管理のために本リポジトリで採用している任意拡張、license は配布条件の明示。
ALLOWED_TOP_LEVEL_KEYS = {"name", "description", "license", "metadata"}

# requirements.md 1.5節に列挙されたホスト固有フロントマターフィールドの既知例。
# ALLOWED_TOP_LEVEL_KEYS に無いキーはこのリストの有無に関わらずすべて違反として扱う。
KNOWN_HOST_SPECIFIC_KEYS = {
    "allowed-tools",
    "disable-model-invocation",
    "context",
}

_FRONTMATTER_DELIM = re.compile(r"^---\s*$")


class FrontmatterError(ValueError):
    """フロントマターの抽出・解析に失敗した場合に送出する。"""


def split_frontmatter(text: str) -> Tuple[str, str]:
    """先頭の`---`区切りYAMLフロントマターと本文を分離して返す。"""

    lines = text.splitlines()
    if not lines or not _FRONTMATTER_DELIM.match(lines[0]):
        raise FrontmatterError("先頭が`---`で始まっていない（フロントマターが無い）")

    end_index = None
    for i in range(1, len(lines)):
        if _FRONTMATTER_DELIM.match(lines[i]):
            end_index = i
            break
    if end_index is None:
        raise FrontmatterError("フロントマターを閉じる`---`が見つからない")

    front = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    return front, body


def parse_simple_yaml_mapping(front: str) -> Dict[str, Any]:
    """`SKILL.md`フロントマターに必要な範囲だけを解釈する最小限のYAMLパーサ。

    対応する形：
    - `key: value`（スカラー、クォート有無を許容）
    - `key: >-` / `key: |` に続く折り返しブロックスカラー（次のトップレベルキーまで）
    - `key:`（値なし）に続くネストしたマッピング（1段のみ、`  subkey: value`）

    本スキルのフロントマターはこの範囲に収まる（`SKILL.md`参照）。汎用YAMLパーサの
    代替ではない。
    """

    result: Dict[str, Any] = {}
    lines = front.splitlines()
    i = 0
    n = len(lines)
    top_key_re = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
    nested_key_re = re.compile(r"^\s{2,}([A-Za-z0-9_-]+):\s*(.*)$")

    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = top_key_re.match(line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()

        if rest in (">-", ">", "|", "|-"):
            # ブロックスカラー：以降のインデントされた行を連結する。
            block_lines: List[str] = []
            i += 1
            while i < n and (lines[i].startswith(" ") or not lines[i].strip()):
                block_lines.append(lines[i].strip())
                i += 1
            result[key] = " ".join(l for l in block_lines if l)
            continue

        if rest == "":
            # 値なし：ネストしたマッピングかどうかを次行で判定する。
            nested: Dict[str, str] = {}
            i += 1
            while i < n and nested_key_re.match(lines[i]):
                nm = nested_key_re.match(lines[i])
                assert nm is not None
                nested[nm.group(1)] = _strip_quotes(nm.group(2).strip())
                i += 1
            result[key] = nested if nested else ""
            continue

        result[key] = _strip_quotes(rest)
        i += 1

    return result


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def load_skill_frontmatter(skill_md_path: Path) -> Dict[str, Any]:
    text = skill_md_path.read_text(encoding="utf-8")
    front, _body = split_frontmatter(text)
    return parse_simple_yaml_mapping(front)


def find_skill_md_files() -> List[Path]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def find_host_specific_fields(frontmatter: Dict[str, Any]) -> List[str]:
    """トップレベルの許可済みキー集合に無いキーをホスト固有フィールドとみなす。"""

    return sorted(k for k in frontmatter.keys() if k not in ALLOWED_TOP_LEVEL_KEYS)
