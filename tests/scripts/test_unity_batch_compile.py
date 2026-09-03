"""unity_batch_compile.py の単体テスト。

実際のUnity実行（サブプロセス起動）は行わない。ログ解析ロジックと、
UNITY_PATH未設定・実行ファイル未検出時のフォールバック挙動のみを検証する。
（requirements.md 5.6節・12.3節、CLAUDE.md 開発フロー）
"""

import importlib.util
import os
import sys
import unittest

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
_MODULE_PATH = os.path.join(
    _REPO_ROOT, "skills", "unity-ugui-runtime-ui", "scripts", "unity_batch_compile.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("unity_batch_compile", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # dataclasses等がモジュールをsys.modulesから解決するため、実行前に登録する。
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ubc = _load_module()


class FindCompileErrorsTest(unittest.TestCase):
    """ログ解析ロジック（error CS 検出）のユニットテスト。サンプル文字列のみを使う。"""

    def test_detects_error_cs_line(self):
        log = (
            "Building...\n"
            "Assets/Scripts/Foo.cs(12,5): error CS0103: The name 'Bar' does not exist\n"
            "Done.\n"
        )
        errors = ubc.find_compile_errors(log)
        self.assertEqual(len(errors), 1)
        self.assertIn("CS0103", errors[0])

    def test_no_error_when_absent(self):
        log = "Building...\nCompilation succeeded.\nDone.\n"
        self.assertEqual(ubc.find_compile_errors(log), [])
        self.assertFalse(ubc.has_compile_errors(log))

    def test_multiple_errors_are_all_detected(self):
        log = (
            "a.cs(1,1): error CS0246: type or namespace not found\n"
            "b.cs(2,2): error CS1002: ; expected\n"
        )
        errors = ubc.find_compile_errors(log)
        self.assertEqual(len(errors), 2)
        self.assertTrue(ubc.has_compile_errors(log))

    def test_empty_log_returns_empty_list(self):
        self.assertEqual(ubc.find_compile_errors(""), [])

    def test_none_like_log_does_not_raise(self):
        self.assertEqual(ubc.find_compile_errors(None), [])

    def test_warning_only_is_not_treated_as_error(self):
        log = "warning CS0168: variable declared but never used\n"
        self.assertEqual(ubc.find_compile_errors(log), [])

    def test_word_containing_error_but_not_pattern_is_ignored(self):
        log = "errorCSharpTool: unrelated line\n"
        self.assertEqual(ubc.find_compile_errors(log), [])


class UnityPathEnvTest(unittest.TestCase):
    """UNITY_PATH の読み取り。値そのものを検証内容以外に用いない。"""

    def test_returns_none_when_unset(self):
        self.assertIsNone(ubc.get_unity_path_from_env({}))

    def test_returns_none_when_empty_string(self):
        self.assertIsNone(ubc.get_unity_path_from_env({"UNITY_PATH": ""}))

    def test_returns_value_when_set(self):
        env = {"UNITY_PATH": "/opt/unity/Unity"}
        self.assertEqual(ubc.get_unity_path_from_env(env), "/opt/unity/Unity")


class ResolveUnityExecutableTest(unittest.TestCase):
    """Windows/macOS/Linuxのパス差（実行ファイル名の違い等）の吸収を検証する。"""

    def test_returns_path_as_is_when_already_a_file(self):
        result = ubc.resolve_unity_executable(
            "/opt/unity/Unity", isfile=lambda p: True, isdir=lambda p: False
        )
        self.assertEqual(result, "/opt/unity/Unity")

    def test_returns_none_when_nothing_matches(self):
        result = ubc.resolve_unity_executable(
            "/does/not/exist", isfile=lambda p: False, isdir=lambda p: False
        )
        self.assertIsNone(result)

    def test_returns_none_for_empty_path(self):
        self.assertIsNone(ubc.resolve_unity_executable(""))

    def test_resolves_windows_executable_inside_directory(self):
        base = "C:\\Unity"
        existing = {os.path.join(base, "Unity.exe")}
        result = ubc.resolve_unity_executable(
            base,
            platform="win32",
            isfile=lambda p: p in existing,
            isdir=lambda p: True,
        )
        self.assertEqual(result, os.path.join(base, "Unity.exe"))

    def test_resolves_macos_app_bundle(self):
        base = "/Applications/Unity.app"
        existing = {os.path.join(base, "Contents", "MacOS", "Unity")}
        result = ubc.resolve_unity_executable(
            base,
            platform="darwin",
            isfile=lambda p: p in existing,
            isdir=lambda p: True,
        )
        self.assertEqual(result, os.path.join(base, "Contents", "MacOS", "Unity"))

    def test_resolves_linux_executable_inside_directory(self):
        base = "/opt/Unity/Editor"
        existing = {os.path.join(base, "Unity")}
        result = ubc.resolve_unity_executable(
            base,
            platform="linux",
            isfile=lambda p: p in existing,
            isdir=lambda p: True,
        )
        self.assertEqual(result, os.path.join(base, "Unity"))


class DetermineVerificationStageTest(unittest.TestCase):
    """UNITY_PATH未設定時に例外を投げず、静的検査段階へ切り替えられる状態を返すことを検証する。"""

    def test_static_only_when_unity_path_not_set(self):
        stage, executable, reason = ubc.determine_verification_stage(env={})
        self.assertEqual(stage, ubc.STAGE_STATIC_ONLY)
        self.assertIsNone(executable)
        self.assertEqual(reason, ubc.REASON_UNITY_PATH_NOT_SET)

    def test_static_only_when_executable_not_found(self):
        stage, executable, reason = ubc.determine_verification_stage(
            env={"UNITY_PATH": "/no/such/unity"},
            isfile=lambda p: False,
            isdir=lambda p: False,
        )
        self.assertEqual(stage, ubc.STAGE_STATIC_ONLY)
        self.assertIsNone(executable)
        self.assertEqual(reason, ubc.REASON_UNITY_EXECUTABLE_NOT_FOUND)

    def test_cli_stage_when_executable_found(self):
        stage, executable, reason = ubc.determine_verification_stage(
            env={"UNITY_PATH": "/opt/unity/Unity"},
            isfile=lambda p: True,
            isdir=lambda p: False,
        )
        self.assertEqual(stage, ubc.STAGE_CLI)
        self.assertEqual(executable, "/opt/unity/Unity")
        self.assertIsNone(reason)

    def test_no_exception_raised_without_unity_path(self):
        try:
            ubc.determine_verification_stage(env={})
        except Exception as exc:  # pragma: no cover - 例外なしを期待
            self.fail(f"unexpected exception raised: {exc}")


class RunUnityBatchCompileWithoutUnityPathTest(unittest.TestCase):
    """UNITY_PATH未設定時、サブプロセスを起動せず static-only な結果を返す。"""

    def test_returns_static_only_result_without_raising(self):
        result = ubc.run_unity_batch_compile("/dummy/project", env={})
        self.assertEqual(result.stage, ubc.STAGE_STATIC_ONLY)
        self.assertIsNone(result.success)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.reason, ubc.REASON_UNITY_PATH_NOT_SET)

    def test_result_never_contains_unity_path_value(self):
        secret_path = "/very/secret/path/to/Unity"
        result = ubc.run_unity_batch_compile(
            "/dummy/project", env={"UNITY_PATH": secret_path}
        )
        result_text = repr(result)
        self.assertNotIn(secret_path, result_text)


class BuildUnityCommandTest(unittest.TestCase):
    """-batchmode -nographics -quit -executeMethod を含むコマンド組み立てを検証する。"""

    def test_includes_required_flags(self):
        command = ubc.build_unity_command(
            "/opt/unity/Unity",
            "/path/to/project",
            "UiBatchCompileCheck.Run",
            "/tmp/log.txt",
        )
        self.assertEqual(command[0], "/opt/unity/Unity")
        self.assertIn("-batchmode", command)
        self.assertIn("-nographics", command)
        self.assertIn("-quit", command)
        self.assertIn("-executeMethod", command)
        self.assertIn("UiBatchCompileCheck.Run", command)
        self.assertIn("-logFile", command)
        self.assertIn("/tmp/log.txt", command)


if __name__ == "__main__":
    unittest.main()
