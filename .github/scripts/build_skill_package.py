#!/usr/bin/env python3
"""`.skill`パッケージを生成する（requirements.md 11.3節 6項目目・12.1節）。

`skills/<skill-name>/`を zip 圧縮し、拡張子を`.skill`にしたものを`dist/`に出力する
簡易実装。パッケージ名には`SKILL.md`の`metadata.version`を用いる。

使い方::

    python3 build_skill_package.py [出力先ディレクトリ（既定: dist）]
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from skill_common import find_skill_md_files, load_skill_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[2]


def build_package(skill_md_path: Path, out_dir: Path) -> Path:
    skill_dir = skill_md_path.parent
    skill_name = skill_dir.name
    frontmatter = load_skill_frontmatter(skill_md_path)
    version = None
    metadata = frontmatter.get("metadata")
    if isinstance(metadata, dict):
        version = metadata.get("version")

    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"-{version}" if version else ""
    package_path = out_dir / f"{skill_name}{suffix}.skill"

    files = sorted(p for p in skill_dir.rglob("*") if p.is_file())
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            # zip内のパスは `<skill-name>/...` に揃える（展開時にディレクトリが
            # そのまま`skills/`配下へ再配置できるようにするため）。
            arcname = str(Path(skill_name) / file_path.relative_to(skill_dir))
            zf.write(file_path, arcname)

    return package_path


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "dist"

    skill_md_files = find_skill_md_files()
    if not skill_md_files:
        print("::error::skills/*/SKILL.md が見つからない", file=sys.stderr)
        return 1

    for skill_md_path in skill_md_files:
        package_path = build_package(skill_md_path, out_dir)
        size_kb = package_path.stat().st_size / 1024
        print(f".skillパッケージを生成: {package_path}（{size_kb:.1f} KiB）")

    return 0


if __name__ == "__main__":
    sys.exit(main())
