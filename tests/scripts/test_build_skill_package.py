"""build_skill_package.py のユニットテスト（red -> green）。

Windows上で`build_package()`を実行すると、zip内エントリ名の生成に
`str(Path(...))`を使っていた場合`\\`区切りになってしまう不具合の再発防止テスト。
zip形式の規約ではエントリ名は常に`/`区切りであるべきで、`\\`区切りだと
Unity・Linux/macOSの展開ツールがディレクトリ構造として認識できない
（フラットなファイル名として扱われる）。標準ライブラリの unittest のみを用いる。
"""

import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / ".github" / "scripts"


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # build_skill_package が `from skill_common import ...` するため必要
    spec.loader.exec_module(module)
    return module


skill_common = _load_module("skill_common", "skill_common.py")
build_skill_package = _load_module("build_skill_package", "build_skill_package.py")


class BuildPackageArcnameTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp_path = Path(self._tmpdir.name)

        # skills/<skill-name>/ 配下にネストしたディレクトリを含む最小構成を作る。
        self.skill_name = "sample-skill"
        self.skill_dir = self.tmp_path / "skills" / self.skill_name
        (self.skill_dir / "scripts").mkdir(parents=True)
        self.skill_md_path = self.skill_dir / "SKILL.md"
        self.skill_md_path.write_text(
            "---\n"
            "name: sample-skill\n"
            "metadata:\n"
            "  version: 1.0.0\n"
            "---\n"
            "本文\n",
            encoding="utf-8",
        )
        (self.skill_dir / "scripts" / "helper.py").write_text("# helper\n", encoding="utf-8")

        self.out_dir = self.tmp_path / "dist"

    def test_arcnames_use_forward_slash_separator(self):
        package_path = build_skill_package.build_package(self.skill_md_path, self.out_dir)

        with zipfile.ZipFile(package_path) as zf:
            names = zf.namelist()

        self.assertTrue(names, "zipにエントリが1つも無い")
        for name in names:
            self.assertNotIn("\\", name, f"zipエントリ名に`\\`が含まれている: {name!r}")

        # ネストしたファイルも`<skill-name>/<サブディレクトリ>/<ファイル名>`の
        # `/`区切りで格納されていることを確認する。
        self.assertIn(f"{self.skill_name}/scripts/helper.py", names)
        self.assertIn(f"{self.skill_name}/SKILL.md", names)

    def test_package_filename_includes_version_suffix(self):
        package_path = build_skill_package.build_package(self.skill_md_path, self.out_dir)
        self.assertEqual(package_path.name, f"{self.skill_name}-1.0.0.skill")


if __name__ == "__main__":
    unittest.main()
