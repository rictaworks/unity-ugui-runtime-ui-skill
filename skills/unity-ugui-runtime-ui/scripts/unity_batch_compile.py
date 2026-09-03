#!/usr/bin/env python3
"""Unity CLI（batchmode）によるコンパイル検証を行うスクリプト。

requirements.md 5.6節（F5：検証／CLI段階）・12.3節（資格情報）・15章（非機能要件）に基づく。

- 標準ライブラリのみで動作する（追加パッケージ不要）。
- Unity実行パスは環境変数 `UNITY_PATH` から読む。値そのものは
  標準出力・標準エラー出力・戻り値の文字列に一切含めない
  （パスが有効かどうかの判定にのみ用いる）。
- `UNITY_PATH` が未設定、または実行ファイルが解決できない場合でも
  例外は投げない。呼び出し元が静的検査段階（static-only）へ
  切り替えられるよう、明確な段階・理由コードを返す。
- Windows・macOS・Linuxで実行ファイル名・配置が異なる差を
  `resolve_unity_executable` が吸収する。
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Sequence, Tuple

# 環境変数名
UNITY_PATH_ENV_VAR = "UNITY_PATH"

# 検証段階
STAGE_STATIC_ONLY = "static-only"
STAGE_CLI = "cli"

# static-only へフォールバックする理由・実行時エラーの理由コード
# （いずれも固定文字列であり、UNITY_PATHの値そのものを含まない）
REASON_UNITY_PATH_NOT_SET = "UNITY_PATH_NOT_SET"
REASON_UNITY_EXECUTABLE_NOT_FOUND = "UNITY_EXECUTABLE_NOT_FOUND"
REASON_PROCESS_TIMEOUT = "PROCESS_TIMEOUT"
REASON_PROCESS_ERROR = "PROCESS_ERROR"

# execute_method の検証エラー理由コード
REASON_EXECUTE_METHOD_NOT_SPECIFIED = "EXECUTE_METHOD_NOT_SPECIFIED"
REASON_EXECUTE_METHOD_PLACEHOLDER_UNRESOLVED = "EXECUTE_METHOD_PLACEHOLDER_UNRESOLVED"

# UiBatchCompileCheck.cs.tmpl の終了コード規約に対応する理由コード
REASON_COMPILE_FAILED = "COMPILE_FAILED"
REASON_TEST_FAILURE = "TEST_FAILURE"
REASON_NO_TESTS_EXECUTED = "NO_TESTS_EXECUTED"
REASON_UNEXPECTED_EXIT_CODE = "UNEXPECTED_EXIT_CODE"

# Unityコンパイルエラーのログパターン（例: "error CS0103: ..."）。
# 成否判定の主軸はsubprocessのreturncodeであり、これは失敗理由の詳細情報としてのみ使う。
_COMPILE_ERROR_PATTERN = re.compile(r"error CS\d+")

# UNITY_PATHがディレクトリを指す場合に探す実行ファイル名（OSごとの差の吸収）
_WINDOWS_CANDIDATE_NAMES: Tuple[str, ...] = ("Unity.exe",)
_MACOS_CANDIDATE_NAMES: Tuple[str, ...] = (
    os.path.join("Contents", "MacOS", "Unity"),
    "Unity",
)
_LINUX_CANDIDATE_NAMES: Tuple[str, ...] = ("Unity",)

# UiBatchCompileCheck.cs.tmpl（EditorApplication.Exit）が設定する終了コード。
# 呼び出し側（本スクリプト）はこれをコンパイル・テストの成否判定の主軸とする。
EXIT_CODE_SUCCESS = 0
EXIT_CODE_COMPILE_ERROR = 1
EXIT_CODE_TEST_FAILURE = 2
EXIT_CODE_NO_TESTS_EXECUTED = 3

# -executeMethod に渡す完全修飾メソッド名。
# 実テンプレート（UiBatchCompileCheck.cs.tmpl）のエントリポイントは
# "{{PROJECT_NAMESPACE}}.EditorTools.UiBatchCompileCheck.CompileAndTest" であり、
# PROJECT_NAMESPACE はプロジェクトごとに異なるプレースホルダーのため、
# このスクリプト側で決め打ちの既定値を持つことができない。
# 呼び出し側（CLIなら --execute-method、プログラムからの呼び出しなら引数）が
# 必ず展開済みの実際の値を明示すること。
DEFAULT_EXECUTE_METHOD: Optional[str] = None
DEFAULT_TIMEOUT_SECONDS = 900


@dataclasses.dataclass(frozen=True)
class CompileResult:
    """検証結果。Unity実行パスの値は保持しない。"""

    stage: str
    success: Optional[bool]
    errors: List[str]
    reason: Optional[str] = None

    @property
    def is_static_only(self) -> bool:
        return self.stage == STAGE_STATIC_ONLY


def find_compile_errors(log_text: Optional[str]) -> List[str]:
    """ログ文字列から `error CS####` を含む行を抽出する。

    実際のUnity実行なしに、サンプルログ文字列だけで検証できる純粋関数。
    """
    if not log_text:
        return []
    return [line for line in log_text.splitlines() if _COMPILE_ERROR_PATTERN.search(line)]


def has_compile_errors(log_text: Optional[str]) -> bool:
    """ログにコンパイルエラーが1件以上含まれるか。"""
    return bool(find_compile_errors(log_text))


def get_unity_path_from_env(env: Optional[Dict[str, str]] = None) -> Optional[str]:
    """`UNITY_PATH` を環境から読む。未設定・空文字なら None を返す。

    戻り値をログ・成果物・内部文書に書き出してはならない
    （呼び出し側の責務。値の有無のみを扱うこと）。
    """
    source = env if env is not None else os.environ
    value = source.get(UNITY_PATH_ENV_VAR)
    if not value:
        return None
    return value


def _candidate_names_for_platform(platform: str) -> Sequence[str]:
    if platform.startswith("win"):
        return _WINDOWS_CANDIDATE_NAMES
    if platform == "darwin":
        return _MACOS_CANDIDATE_NAMES
    return _LINUX_CANDIDATE_NAMES


def resolve_unity_executable(
    unity_path: Optional[str],
    platform: Optional[str] = None,
    isfile=os.path.isfile,
    isdir=os.path.isdir,
) -> Optional[str]:
    """`UNITY_PATH` の値からUnity実行ファイルの実パスを解決する。

    Windows（`Unity.exe`）・macOS（`.app`バンドル内の`Contents/MacOS/Unity`）・
    Linux（`Unity`）の実行ファイル名・配置差を吸収する。

    - 値がそのままファイルであればそれを返す。
    - 値がディレクトリであれば、対象OSの既定の実行ファイル名を探す。
    - どちらでもなければ None を返す（例外は投げない）。
    """
    if not unity_path:
        return None
    if isfile(unity_path):
        return unity_path
    if isdir(unity_path):
        for name in _candidate_names_for_platform(platform if platform is not None else sys.platform):
            candidate = os.path.join(unity_path, name)
            if isfile(candidate):
                return candidate
    return None


def determine_verification_stage(
    env: Optional[Dict[str, str]] = None,
    platform: Optional[str] = None,
    isfile=os.path.isfile,
    isdir=os.path.isdir,
) -> Tuple[str, Optional[str], Optional[str]]:
    """検証段階を決定する。例外は投げない。

    戻り値: (stage, executable_or_None, reason_or_None)
    `UNITY_PATH` が未設定、または実行ファイルが解決できない場合は
    `STAGE_STATIC_ONLY` を返し、呼び出し元が静的検査段階へ
    明確に切り替えられるようにする。
    """
    unity_path = get_unity_path_from_env(env)
    if unity_path is None:
        return STAGE_STATIC_ONLY, None, REASON_UNITY_PATH_NOT_SET

    executable = resolve_unity_executable(unity_path, platform=platform, isfile=isfile, isdir=isdir)
    if executable is None:
        return STAGE_STATIC_ONLY, None, REASON_UNITY_EXECUTABLE_NOT_FOUND

    return STAGE_CLI, executable, None


def build_unity_command(
    executable: str,
    project_path: str,
    execute_method: str,
    log_file_path: str,
) -> List[str]:
    """`-batchmode -nographics -quit -executeMethod` を含むコマンド引数列を組み立てる。

    サブプロセス実行なしにテストできる純粋関数。
    """
    return [
        executable,
        "-batchmode",
        "-nographics",
        "-quit",
        "-projectPath",
        project_path,
        "-executeMethod",
        execute_method,
        "-logFile",
        log_file_path,
    ]


def _validate_execute_method(execute_method: Optional[str]) -> Optional[str]:
    """execute_method が実際にUnity側で解決可能な値かを検証する。

    `DEFAULT_EXECUTE_METHOD`（None）のまま・空文字のまま呼ばれた場合や、
    テンプレートの `{{PROJECT_NAMESPACE}}` 等のプレースホルダーが未展開のまま
    渡された場合に、サブプロセスを起動する前に検出できるようにする。

    戻り値: 問題があれば理由コード、無ければ None。
    """
    if not execute_method:
        return REASON_EXECUTE_METHOD_NOT_SPECIFIED
    if "{{" in execute_method or "}}" in execute_method:
        return REASON_EXECUTE_METHOD_PLACEHOLDER_UNRESOLVED
    return None


def _build_result_from_exit_code(returncode: int, errors: List[str]) -> CompileResult:
    """UiBatchCompileCheck.cs.tmpl の終了コード規約に基づき CompileResult を組み立てる。

    成否判定の主軸は returncode であり、ログからの `error CS` 抽出（`errors`）は
    失敗理由の詳細情報としてのみ用いる。テスト失敗・テスト未実施のログには
    `error CS` という文字列が含まれないため、ログの正規表現一致だけに頼ると
    誤って成功と判定してしまう。
    """
    if returncode == EXIT_CODE_SUCCESS:
        return CompileResult(stage=STAGE_CLI, success=True, errors=errors, reason=None)
    if returncode == EXIT_CODE_COMPILE_ERROR:
        return CompileResult(stage=STAGE_CLI, success=False, errors=errors, reason=REASON_COMPILE_FAILED)
    if returncode == EXIT_CODE_TEST_FAILURE:
        return CompileResult(stage=STAGE_CLI, success=False, errors=errors, reason=REASON_TEST_FAILURE)
    if returncode == EXIT_CODE_NO_TESTS_EXECUTED:
        # 不変条件12（実施していない検証を実施済みとしない）：テスト未実施は成功として扱わない。
        return CompileResult(stage=STAGE_CLI, success=False, errors=errors, reason=REASON_NO_TESTS_EXECUTED)
    return CompileResult(stage=STAGE_CLI, success=False, errors=errors, reason=REASON_UNEXPECTED_EXIT_CODE)


def run_unity_batch_compile(
    project_path: str,
    execute_method: Optional[str] = DEFAULT_EXECUTE_METHOD,
    env: Optional[Dict[str, str]] = None,
    platform: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> CompileResult:
    """Unity CLIバッチコンパイル（コンパイル＋`UiBatchCompileCheck`）を実行する。

    `UNITY_PATH` が未設定、または実行ファイルが解決できない場合は
    例外を投げず、`STAGE_STATIC_ONLY` の `CompileResult` を返す。
    戻り値には `UNITY_PATH` の値（実行ファイルの実パスを含む）を含めない。

    `execute_method` は既定値を持たない（`DEFAULT_EXECUTE_METHOD` は None）。
    CLI段階に進んだ状態で未指定・未展開のプレースホルダーのまま渡された場合は、
    サブプロセスを起動せず理由コード付きの失敗結果を返す。
    """
    stage, executable, reason = determine_verification_stage(env=env, platform=platform)
    if stage == STAGE_STATIC_ONLY or executable is None:
        return CompileResult(stage=STAGE_STATIC_ONLY, success=None, errors=[], reason=reason)

    validation_reason = _validate_execute_method(execute_method)
    if validation_reason is not None:
        return CompileResult(stage=STAGE_CLI, success=False, errors=[], reason=validation_reason)

    with tempfile.TemporaryDirectory() as tmp_dir:
        log_file_path = os.path.join(tmp_dir, "unity_batch_compile.log")
        command = build_unity_command(executable, project_path, execute_method, log_file_path)
        try:
            completed = subprocess.run(
                command,
                timeout=timeout,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return CompileResult(stage=STAGE_CLI, success=False, errors=[], reason=REASON_PROCESS_TIMEOUT)
        except OSError:
            return CompileResult(stage=STAGE_CLI, success=False, errors=[], reason=REASON_PROCESS_ERROR)

        log_text = ""
        if os.path.isfile(log_file_path):
            with open(log_file_path, "r", encoding="utf-8", errors="replace") as log_file:
                log_text = log_file.read()

        errors = find_compile_errors(log_text)
        return _build_result_from_exit_code(completed.returncode, errors)


def _format_result_for_output(result: CompileResult) -> str:
    """CompileResultを人間可読な文字列に整形する。UNITY_PATHの値は含まない。"""
    lines = [f"stage: {result.stage}"]
    if result.reason is not None:
        lines.append(f"reason: {result.reason}")
    if result.success is not None:
        lines.append(f"success: {result.success}")
    if result.errors:
        lines.append("errors:")
        lines.extend(f"  {line}" for line in result.errors)
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "UNITY_PATH を用いてUnityのバッチコンパイル検証を行う。"
            "UNITY_PATH未設定時・実行ファイル未検出時は例外を投げず"
            "static-only段階の結果を返す。"
        )
    )
    parser.add_argument("project_path", help="Unityプロジェクトのパス")
    parser.add_argument(
        "--execute-method",
        required=True,
        help=(
            "実行する完全修飾staticメソッド名。既定値は無い"
            "（UiBatchCompileCheck.cs.tmpl のエントリポイントは "
            "'{PROJECT_NAMESPACE}.EditorTools.UiBatchCompileCheck.CompileAndTest' で、"
            "PROJECT_NAMESPACE はプロジェクトごとに異なる名前空間へ置換済みの値を渡すこと。"
            "例: MyProject.EditorTools.UiBatchCompileCheck.CompileAndTest）"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"サブプロセスのタイムアウト秒数（既定: {DEFAULT_TIMEOUT_SECONDS}）",
    )
    args = parser.parse_args(argv)

    result = run_unity_batch_compile(
        args.project_path,
        execute_method=args.execute_method,
        timeout=args.timeout,
    )
    print(_format_result_for_output(result))

    if result.stage == STAGE_STATIC_ONLY:
        return 0
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
