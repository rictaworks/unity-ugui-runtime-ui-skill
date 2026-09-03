#!/usr/bin/env python3
"""`SKILL.md`のフロントマターと命名を検証する（requirements.md 11.3節 1項目目）。

`skills-ref validate`という外部ツールは存在しないため、その相当チェックを
Python標準ライブラリのみで自作したもの。検査内容：

1. フロントマターに必須フィールド（`name`・`description`・`license`・
   `metadata.version`）が揃っている
2. `name`がkebab-case（英小文字・数字・ハイフンのみ）であり、
   `skills/<name>/SKILL.md`の`<name>`（ディレクトリ名）と一致する
3. `description`が空でなく、極端に長すぎない（発火条件として機能する分量）
4. `metadata.version`がセマンティックバージョン形式（例：`0.1.0`）
5. トップレベルにホスト固有フィールド（`allowed-tools`・
   `disable-model-invocation`・`context`等）が含まれていない
   （requirements.md 1.5節）

使い方::

    python3 validate_frontmatter.py
"""

from __future__ import annotations

import sys

from skill_common import (
    FrontmatterError,
    find_host_specific_fields,
    find_skill_md_files,
    load_skill_frontmatter,
)

_NAME_RE_STR = r"^[a-z0-9]+(-[a-z0-9]+)*$"
_SEMVER_RE_STR = r"^\d+\.\d+\.\d+$"

_MAX_DESCRIPTION_LENGTH = 1024


def _matches(pattern: str, value: str) -> bool:
    import re

    return re.match(pattern, value) is not None


def validate_one(skill_md_path) -> list:
    errors: list = []
    skill_dir_name = skill_md_path.parent.name

    try:
        frontmatter = load_skill_frontmatter(skill_md_path)
    except FrontmatterError as e:
        return [f"{skill_md_path}: フロントマターの解析に失敗した: {e}"]

    # 1. 必須フィールド
    for field in ("name", "description", "license"):
        if not frontmatter.get(field):
            errors.append(f"{skill_md_path}: 必須フィールド `{field}` が無い、または空")

    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict) or not metadata.get("version"):
        errors.append(f"{skill_md_path}: 必須フィールド `metadata.version` が無い、または空")
    elif not _matches(_SEMVER_RE_STR, str(metadata["version"])):
        errors.append(
            f"{skill_md_path}: `metadata.version` がセマンティックバージョン形式でない: "
            f"{metadata['version']!r}"
        )

    # 2. name の命名規則・ディレクトリ名との一致
    name = frontmatter.get("name")
    if name:
        if not _matches(_NAME_RE_STR, str(name)):
            errors.append(
                f"{skill_md_path}: `name` はkebab-case（英小文字・数字・ハイフン）で"
                f"ある必要がある: {name!r}"
            )
        if name != skill_dir_name:
            errors.append(
                f"{skill_md_path}: `name`（{name!r}）が配置ディレクトリ名"
                f"（{skill_dir_name!r}）と一致しない"
            )

    # 3. description の分量
    description = frontmatter.get("description")
    if isinstance(description, str):
        if len(description) > _MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"{skill_md_path}: `description` が長すぎる"
                f"（{len(description)}文字 > {_MAX_DESCRIPTION_LENGTH}）"
            )

    # 5. ホスト固有フロントマターフィールド
    host_specific = find_host_specific_fields(frontmatter)
    if host_specific:
        errors.append(
            f"{skill_md_path}: ホスト固有フロントマターフィールドを含む: "
            f"{', '.join(host_specific)}（requirements.md 1.5節により使用禁止）"
        )

    return errors


def main() -> int:
    skill_md_files = find_skill_md_files()
    if not skill_md_files:
        print("::error::skills/*/SKILL.md が見つからない", file=sys.stderr)
        return 1

    all_errors: list = []
    for path in skill_md_files:
        all_errors.extend(validate_one(path))

    if all_errors:
        for err in all_errors:
            print(f"::error::{err}", file=sys.stderr)
        print(f"\nフロントマター検証: {len(all_errors)}件の違反", file=sys.stderr)
        return 1

    print(f"フロントマター検証: OK（{len(skill_md_files)}件のSKILL.mdを検証）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
