#!/usr/bin/env python3
"""禁止内容を検査する（requirements.md 11.3節 4項目目）。

検査対象は成果物（`skills/<skill-name>/`配下の全ファイル）。以下4種を検出する：

1. 資格情報らしき文字列（AWS/GitHub/Slackの既知トークン形式、PEM秘密鍵ヘッダ、
   `password = "..."`のような代入パターン等）
2. メールアドレス
3. 個人名らしき固有名詞（`Author:`等の署名パターンのヒューリスティック検出、
   および`forbidden_names.txt`の追加パターン）
4. ホスト固有フロントマターフィールド（`SKILL.md`のフロントマター）

正規表現ベースの簡易検査であり、完全な検出を保証しない（既知の限界）。

使い方::

    python3 check_forbidden_content.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Tuple

from skill_common import (
    SKILLS_DIR,
    find_host_specific_fields,
    find_skill_md_files,
    load_skill_frontmatter,
)

SCRIPT_DIR = Path(__file__).resolve().parent
FORBIDDEN_NAMES_FILE = SCRIPT_DIR / "forbidden_names.txt"

# --- 1. 資格情報らしき文字列 -------------------------------------------------

_CREDENTIAL_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "github_token",
        re.compile(r"\b(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b"),
    ),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "pem_private_key",
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |)PRIVATE KEY-----"),
    ),
    (
        "generic_secret_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|password|passwd|token|access[_-]?key)\b"
            r"\s*[:=]\s*['\"][A-Za-z0-9/+_=.-]{8,}['\"]"
        ),
    ),
]

# --- 2. メールアドレス -------------------------------------------------------

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# --- 3. 個人名らしき固有名詞（署名パターンのヒューリスティック） ------------

_SIGNATURE_NAME_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    (
        "latin_author_signature",
        re.compile(
            r"(?im)^\s*(author|written by|by|contact|maintainer)\s*[:：]\s*"
            r"[A-Z][a-zA-Z.'-]+(\s+[A-Z][a-zA-Z.'-]+){1,2}\s*$"
        ),
    ),
    (
        "japanese_author_signature",
        re.compile(
            r"(?im)^\s*(作成者|担当者|連絡先|著者)\s*[:：]\s*"
            r"[^\s（(【].{1,30}$"
        ),
    ),
]


def _load_forbidden_name_patterns() -> List["re.Pattern[str]"]:
    patterns: List["re.Pattern[str]"] = []
    if not FORBIDDEN_NAMES_FILE.is_file():
        return patterns
    for raw_line in FORBIDDEN_NAMES_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            patterns.append(re.compile(line, re.IGNORECASE))
        except re.error as e:
            print(
                f"::warning::forbidden_names.txt の行が不正な正規表現: "
                f"{line!r} ({e})",
                file=sys.stderr,
            )
    return patterns


# --- 走査対象ファイル ---------------------------------------------------------

_TEXT_SUFFIXES = {".md", ".py", ".tmpl", ".txt", ".json", ".yml", ".yaml", ".cs"}


def _iter_target_files():
    if not SKILLS_DIR.is_dir():
        return
    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        for path in sorted(skill_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in _TEXT_SUFFIXES:
                continue
            yield path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def check_file(path: Path, forbidden_name_patterns: List["re.Pattern[str]"]) -> List[str]:
    errors = []
    text = _read_text(path)
    if not text:
        return errors

    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule_id, pattern in _CREDENTIAL_PATTERNS:
            if pattern.search(line):
                errors.append(
                    f"{path}:{lineno}: 資格情報らしき文字列を検出（{rule_id}）"
                )
        if _EMAIL_RE.search(line):
            errors.append(f"{path}:{lineno}: メールアドレスらしき文字列を検出")
        for rule_id, pattern in _SIGNATURE_NAME_PATTERNS:
            if pattern.search(line):
                errors.append(
                    f"{path}:{lineno}: 個人名らしき署名パターンを検出（{rule_id}）"
                )
        for pattern in forbidden_name_patterns:
            if pattern.search(line):
                errors.append(
                    f"{path}:{lineno}: forbidden_names.txt に登録された"
                    f"パターンに一致（{pattern.pattern!r}）"
                )
    return errors


def check_host_specific_frontmatter_fields() -> List[str]:
    errors = []
    for skill_md_path in find_skill_md_files():
        frontmatter = load_skill_frontmatter(skill_md_path)
        host_specific = find_host_specific_fields(frontmatter)
        if host_specific:
            errors.append(
                f"{skill_md_path}: ホスト固有フロントマターフィールドを含む: "
                f"{', '.join(host_specific)}"
            )
    return errors


def main() -> int:
    forbidden_name_patterns = _load_forbidden_name_patterns()

    all_errors: List[str] = []
    checked_files = 0
    for path in _iter_target_files():
        checked_files += 1
        all_errors.extend(check_file(path, forbidden_name_patterns))

    all_errors.extend(check_host_specific_frontmatter_fields())

    if all_errors:
        for err in all_errors:
            print(f"::error::{err}", file=sys.stderr)
        print(f"\n禁止内容検査: {len(all_errors)}件の違反", file=sys.stderr)
        return 1

    print(f"禁止内容検査: OK（{checked_files}ファイルを検査）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
