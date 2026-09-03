#!/usr/bin/env python3
"""`SKILL.md`の行数上限と、参照ファイルの目次有無を検査する（requirements.md 11.3節 2項目目）。

- `SKILL.md`：500行以下（7.2節の上限）。250〜300行は目標値であり本検査では強制しない。
- `references/*`：300行を超えるファイルには目次（見出し「目次」または「Table of
  Contents」）が必要（7.2節）。

使い方::

    python3 check_skill_md_length.py
"""

from __future__ import annotations

import re
import sys

from skill_common import find_skill_md_files

SKILL_MD_MAX_LINES = 500
REFERENCE_TOC_THRESHOLD_LINES = 300

_TOC_HEADING_RE = re.compile(
    r"^#{1,6}\s*(目次|table of contents)\s*$", re.IGNORECASE
)


def _count_lines(text: str) -> int:
    if text == "":
        return 0
    # 末尾の改行の有無に関わらず「行数」として自然な値を返す。
    return len(text.splitlines())


def check_skill_md(skill_md_path) -> list:
    errors = []
    text = skill_md_path.read_text(encoding="utf-8")
    n_lines = _count_lines(text)
    if n_lines > SKILL_MD_MAX_LINES:
        errors.append(
            f"{skill_md_path}: 行数が上限を超えている（{n_lines}行 > "
            f"{SKILL_MD_MAX_LINES}行）"
        )
    return errors


def check_reference_files(skill_md_path) -> list:
    errors = []
    references_dir = skill_md_path.parent / "references"
    if not references_dir.is_dir():
        return errors

    for ref_path in sorted(references_dir.glob("*.md")):
        text = ref_path.read_text(encoding="utf-8")
        n_lines = _count_lines(text)
        if n_lines <= REFERENCE_TOC_THRESHOLD_LINES:
            continue
        has_toc = any(_TOC_HEADING_RE.match(line.strip()) for line in text.splitlines())
        if not has_toc:
            errors.append(
                f"{ref_path}: {n_lines}行あり{REFERENCE_TOC_THRESHOLD_LINES}行を超える"
                "が、「目次」見出しが無い"
            )
    return errors


def main() -> int:
    skill_md_files = find_skill_md_files()
    if not skill_md_files:
        print("::error::skills/*/SKILL.md が見つからない", file=sys.stderr)
        return 1

    all_errors: list = []
    for skill_md_path in skill_md_files:
        all_errors.extend(check_skill_md(skill_md_path))
        all_errors.extend(check_reference_files(skill_md_path))

    if all_errors:
        for err in all_errors:
            print(f"::error::{err}", file=sys.stderr)
        print(f"\n行数・目次検証: {len(all_errors)}件の違反", file=sys.stderr)
        return 1

    print("行数・目次検証: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
