#!/usr/bin/env python3
"""UiTheme の前景・背景色の組み合わせについて、WCAG 2.0 のコントラスト比を検査する。

requirements.md 5.6節・6章不変条件10に基づく静的検査スクリプト。
標準ライブラリのみで動作する（追加パッケージを要求しない）。

使い方:
    python3 check_contrast.py <前景色1> <背景色1> [<前景色2> <背景色2> ...] [--threshold 4.5]

色は16進カラーコードで指定する（例: #FFFFFF, ffffff, #fff）。
コントラスト比が閾値（既定4.5）未満の組み合わせが1件でもあれば、
非ゼロの終了コードで報告する。
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Tuple

DEFAULT_THRESHOLD = 4.5

RgbColor = Tuple[int, int, int]


def parse_hex_color(value: str) -> RgbColor:
    """16進カラーコードを (R, G, B) の整数タプル（各0〜255）に変換する。

    先頭の '#' の有無を許容する。3桁省略形（例: '0f0'）と6桁（例: '00ff00'）に対応する。
    不正な形式・不正な文字の場合は ValueError を送出する。
    """
    text = value.strip()
    if text.startswith("#"):
        text = text[1:]

    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)

    if len(text) != 6:
        raise ValueError(f"不正な16進カラーコードです（桁数）: {value!r}")

    try:
        r = int(text[0:2], 16)
        g = int(text[2:4], 16)
        b = int(text[4:6], 16)
    except ValueError as exc:
        raise ValueError(f"不正な16進カラーコードです（16進数以外の文字）: {value!r}") from exc

    return (r, g, b)


def _linearize_channel(channel_8bit: int) -> float:
    """sRGBの1チャンネル値（0〜255）をWCAG式の線形値に変換する。"""
    c = channel_8bit / 255.0
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: RgbColor) -> float:
    """WCAG 2.0 の相対輝度 L を計算する。"""
    r, g, b = rgb
    r_lin = _linearize_channel(r)
    g_lin = _linearize_channel(g)
    b_lin = _linearize_channel(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(rgb1: RgbColor, rgb2: RgbColor) -> float:
    """2色間のWCAG 2.0コントラスト比 (L1+0.05)/(L2+0.05) を計算する（L1が明るい方）。"""
    l1 = relative_luminance(rgb1)
    l2 = relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def is_sufficient(ratio: float, threshold: float = DEFAULT_THRESHOLD) -> bool:
    """コントラスト比が閾値以上かどうかを判定する。"""
    return ratio >= threshold


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_contrast.py",
        description=(
            "UiTheme の前景・背景色の組み合わせについて、"
            "WCAG 2.0 のコントラスト比を検査する。"
        ),
    )
    parser.add_argument(
        "colors",
        nargs="*",
        metavar="COLOR",
        help="16進カラーコードを前景・背景の順で偶数個指定する（例: #000000 #FFFFFF）",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"合格とみなす最小コントラスト比（既定 {DEFAULT_THRESHOLD}）",
    )
    return parser


def main(argv: List[str]) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if not args.colors:
        parser.print_usage(sys.stderr)
        print("エラー: 色ペアを1組以上指定してください。", file=sys.stderr)
        return 2

    if len(args.colors) % 2 != 0:
        parser.print_usage(sys.stderr)
        print("エラー: 色は前景・背景の対で偶数個指定してください。", file=sys.stderr)
        return 2

    all_passed = True
    for index in range(0, len(args.colors), 2):
        fg_raw = args.colors[index]
        bg_raw = args.colors[index + 1]

        try:
            fg = parse_hex_color(fg_raw)
            bg = parse_hex_color(bg_raw)
        except ValueError as exc:
            print(f"エラー: {exc}", file=sys.stderr)
            return 2

        ratio = contrast_ratio(fg, bg)
        passed = is_sufficient(ratio, threshold=args.threshold)
        status = "OK" if passed else "NG"
        print(f"{status} {fg_raw} on {bg_raw}: {ratio:.2f} (threshold {args.threshold})")

        if not passed:
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
