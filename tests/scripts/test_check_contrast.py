"""check_contrast.py のユニットテスト（red -> green）。

requirements.md 5.6節・6章不変条件10に基づき、WCAG 2.0の相対輝度式による
コントラスト比計算の正しさと、4.5未満の組み合わせを検出するロジックを検証する。
標準ライブラリの unittest のみを用いる。
"""

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "unity-ugui-runtime-ui"
    / "scripts"
    / "check_contrast.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("check_contrast", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_contrast = _load_module()


class ParseHexColorTests(unittest.TestCase):
    def test_parses_six_digit_with_hash(self):
        self.assertEqual(check_contrast.parse_hex_color("#FFFFFF"), (255, 255, 255))

    def test_parses_six_digit_without_hash(self):
        self.assertEqual(check_contrast.parse_hex_color("000000"), (0, 0, 0))

    def test_parses_three_digit_shorthand(self):
        self.assertEqual(check_contrast.parse_hex_color("#0f0"), (0, 255, 0))

    def test_parses_case_insensitively(self):
        self.assertEqual(check_contrast.parse_hex_color("#aAbBcC"), (170, 187, 204))

    def test_rejects_invalid_length(self):
        with self.assertRaises(ValueError):
            check_contrast.parse_hex_color("#ABCD")

    def test_rejects_non_hex_characters(self):
        with self.assertRaises(ValueError):
            check_contrast.parse_hex_color("#GGGGGG")


class RelativeLuminanceTests(unittest.TestCase):
    def test_black_is_zero(self):
        self.assertAlmostEqual(check_contrast.relative_luminance((0, 0, 0)), 0.0, places=6)

    def test_white_is_one(self):
        self.assertAlmostEqual(check_contrast.relative_luminance((255, 255, 255)), 1.0, places=6)

    def test_mid_gray_matches_known_value(self):
        # #767676 は WCAG 資料でよく参照される既知の中間色。
        luminance = check_contrast.relative_luminance((0x76, 0x76, 0x76))
        self.assertAlmostEqual(luminance, 0.1811, places=3)


class ContrastRatioTests(unittest.TestCase):
    def test_black_on_white_is_21_to_1(self):
        ratio = check_contrast.contrast_ratio((0, 0, 0), (255, 255, 255))
        self.assertAlmostEqual(ratio, 21.0, places=2)

    def test_white_on_black_is_symmetric(self):
        ratio = check_contrast.contrast_ratio((255, 255, 255), (0, 0, 0))
        self.assertAlmostEqual(ratio, 21.0, places=2)

    def test_same_color_is_1_to_1(self):
        ratio = check_contrast.contrast_ratio((0x33, 0x66, 0x99), (0x33, 0x66, 0x99))
        self.assertAlmostEqual(ratio, 1.0, places=6)

    def test_known_pair_767676_on_white_is_about_4_54(self):
        ratio = check_contrast.contrast_ratio((0x76, 0x76, 0x76), (0xFF, 0xFF, 0xFF))
        self.assertAlmostEqual(ratio, 4.54, places=1)

    def test_known_failing_pair_999999_on_white_is_below_threshold(self):
        ratio = check_contrast.contrast_ratio((0x99, 0x99, 0x99), (0xFF, 0xFF, 0xFF))
        self.assertLess(ratio, 4.5)
        self.assertAlmostEqual(ratio, 2.85, places=1)


class IsSufficientTests(unittest.TestCase):
    def test_ratio_at_threshold_passes(self):
        self.assertTrue(check_contrast.is_sufficient(4.5))

    def test_ratio_above_threshold_passes(self):
        self.assertTrue(check_contrast.is_sufficient(21.0))

    def test_ratio_below_threshold_fails(self):
        self.assertFalse(check_contrast.is_sufficient(4.49))

    def test_custom_threshold(self):
        self.assertTrue(check_contrast.is_sufficient(3.0, threshold=3.0))
        self.assertFalse(check_contrast.is_sufficient(2.99, threshold=3.0))


class MainCliTests(unittest.TestCase):
    def _run_main(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = check_contrast.main(argv)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_black_white_pair_passes_with_zero_exit_code(self):
        exit_code, out, _err = self._run_main(["#000000", "#FFFFFF"])
        self.assertEqual(exit_code, 0)
        self.assertIn("21.0", out)

    def test_low_contrast_pair_returns_nonzero_exit_code(self):
        exit_code, out, _err = self._run_main(["#999999", "#FFFFFF"])
        self.assertNotEqual(exit_code, 0)
        self.assertIn("2.8", out)

    def test_multiple_pairs_any_failure_makes_nonzero_exit_code(self):
        exit_code, _out, _err = self._run_main(
            ["#000000", "#FFFFFF", "#999999", "#FFFFFF"]
        )
        self.assertNotEqual(exit_code, 0)

    def test_all_pairs_passing_returns_zero_exit_code(self):
        exit_code, _out, _err = self._run_main(
            ["#000000", "#FFFFFF", "#767676", "#FFFFFF"]
        )
        self.assertEqual(exit_code, 0)

    def test_odd_number_of_colors_is_a_usage_error(self):
        exit_code, _out, err = self._run_main(["#000000"])
        self.assertNotEqual(exit_code, 0)
        self.assertTrue(err)

    def test_no_arguments_is_a_usage_error(self):
        exit_code, _out, err = self._run_main([])
        self.assertNotEqual(exit_code, 0)
        self.assertTrue(err)

    def test_invalid_hex_code_is_reported_as_error(self):
        exit_code, _out, err = self._run_main(["#ZZZZZZ", "#FFFFFF"])
        self.assertNotEqual(exit_code, 0)
        self.assertTrue(err)

    def test_custom_threshold_option(self):
        # #999999 on #FFFFFF の実際の比率は約2.85のため、閾値をそれより低く設定して合格させる。
        exit_code, _out, _err = self._run_main(
            ["--threshold", "2.5", "#999999", "#FFFFFF"]
        )
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
