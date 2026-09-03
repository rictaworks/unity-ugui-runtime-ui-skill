#!/usr/bin/env python3
"""参照ファイルへの相対リンクの存在確認を行う（requirements.md 11.3節 3項目目）。

`skills/<skill-name>/`配下のMarkdownファイルに書かれた相対リンク
（`[text](path)`形式。URL・アンカーのみのリンク・`mailto:`は対象外）について、
1階層まで（スキルディレクトリの外に`../`で1段以上出ない範囲）でリンク先の
ファイルが実在するかを確認する。

使い方::

    python3 check_relative_links.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from skill_common import SKILLS_DIR

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_SKIP_SCHEMES = ("http://", "https://", "mailto:", "#")


def _iter_markdown_files(skill_dir: Path):
    yield skill_dir / "SKILL.md"
    for sub in ("references", "assets"):
        d = skill_dir / sub
        if d.is_dir():
            yield from sorted(d.glob("*.md"))


def _resolve_target(link: str) -> str:
    # `path#anchor` や `path "title"` からパス部分のみを取り出す。
    path_part = link.strip()
    if " " in path_part:
        path_part = path_part.split(" ", 1)[0]
    path_part = path_part.split("#", 1)[0].strip()
    return path_part


def check_file(md_path: Path, skill_dir: Path) -> list:
    errors = []
    text = md_path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _LINK_RE.finditer(line):
            raw_target = match.group(1).strip()
            if not raw_target or raw_target.startswith(_SKIP_SCHEMES):
                continue
            target_path_str = _resolve_target(raw_target)
            if not target_path_str:
                # アンカーのみのリンク（同一ファイル内）。
                continue
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target_path_str):
                # http/https/mailto以外のスキーム付きリンクは対象外とする。
                continue

            resolved = (md_path.parent / target_path_str).resolve()

            try:
                resolved.relative_to(skill_dir.resolve().parent)
            except ValueError:
                errors.append(
                    f"{md_path}:{lineno}: 相対リンク `{raw_target}` がスキル"
                    "ディレクトリの外（1階層を超えて）を指している"
                )
                continue

            if not resolved.exists():
                errors.append(
                    f"{md_path}:{lineno}: 相対リンク `{raw_target}` の参照先が"
                    f"存在しない（解決先: {resolved}）"
                )
    return errors


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print("::error::skills/ が見つからない", file=sys.stderr)
        return 1

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    if not skill_dirs:
        print("::error::skills/ 配下にスキルディレクトリが無い", file=sys.stderr)
        return 1

    all_errors: list = []
    checked_files = 0
    for skill_dir in skill_dirs:
        for md_path in _iter_markdown_files(skill_dir):
            if not md_path.is_file():
                continue
            checked_files += 1
            all_errors.extend(check_file(md_path, skill_dir))

    if all_errors:
        for err in all_errors:
            print(f"::error::{err}", file=sys.stderr)
        print(f"\n相対リンク検証: {len(all_errors)}件の違反", file=sys.stderr)
        return 1

    print(f"相対リンク検証: OK（{checked_files}ファイルを検査）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
