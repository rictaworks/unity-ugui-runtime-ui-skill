"""unity_batch_compile.py の単体テスト。

実際のUnity実行（サブプロセス起動）は行わない。ログ解析ロジックと、
UNITY_PATH未設定・実行ファイル未検出時のフォールバック挙動のみを検証する。
（requirements.md 5.6節・12.3節、CLAUDE.md 開発フロー）
"""

import importlib.util
import os
import sys
import unittest
from unittest import mock

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


class ExecuteMethodValidationTest(unittest.TestCase):
    """不具合3の修正：DEFAULT_EXECUTE_METHODが実テンプレートのエントリポイントと一致しない問題。

    PROJECT_NAMESPACEはプロジェクト固有のプレースホルダーであり、スクリプト側で
    決め打ちできない。既定値はNoneとし、CLI段階でexecute_methodが未指定・未展開の
    場合は例外を投げず、サブプロセスを起動せずに明確な理由コード付きで失敗を返す。
    """

    def test_default_execute_method_is_none(self):
        # 実テンプレートのエントリポイントは {{PROJECT_NAMESPACE}}.EditorTools.UiBatchCompileCheck.CompileAndTest
        # であり、名前空間はプロジェクトごとに異なるため、決め打ちのデフォルト値を持てない。
        self.assertIsNone(ubc.DEFAULT_EXECUTE_METHOD)

    def test_cli_stage_without_execute_method_fails_without_running_subprocess(self):
        with mock.patch.object(
            ubc,
            "determine_verification_stage",
            return_value=(ubc.STAGE_CLI, "/opt/unity/Unity", None),
        ), mock.patch.object(ubc.subprocess, "run") as mock_run:
            result = ubc.run_unity_batch_compile("/dummy/project")  # execute_method未指定

        mock_run.assert_not_called()
        self.assertEqual(result.stage, ubc.STAGE_CLI)
        self.assertFalse(result.success)
        self.assertEqual(result.reason, ubc.REASON_EXECUTE_METHOD_NOT_SPECIFIED)

    def test_cli_stage_with_unresolved_placeholder_fails_without_running_subprocess(self):
        with mock.patch.object(
            ubc,
            "determine_verification_stage",
            return_value=(ubc.STAGE_CLI, "/opt/unity/Unity", None),
        ), mock.patch.object(ubc.subprocess, "run") as mock_run:
            result = ubc.run_unity_batch_compile(
                "/dummy/project",
                execute_method="{{PROJECT_NAMESPACE}}.EditorTools.UiBatchCompileCheck.CompileAndTest",
            )

        mock_run.assert_not_called()
        self.assertEqual(result.stage, ubc.STAGE_CLI)
        self.assertFalse(result.success)
        self.assertEqual(result.reason, ubc.REASON_EXECUTE_METHOD_PLACEHOLDER_UNRESOLVED)

    def test_static_only_stage_does_not_require_execute_method(self):
        # UNITY_PATH未設定なら、execute_method未指定でも既存どおりstatic-onlyの結果を返す
        # （呼び出し側の既存の使い方を壊さない）。
        result = ubc.run_unity_batch_compile("/dummy/project", env={})
        self.assertEqual(result.stage, ubc.STAGE_STATIC_ONLY)
        self.assertIsNone(result.success)


class RunUnityBatchCompileExitCodeTest(unittest.TestCase):
    """不具合4の修正：成否判定はsubprocessのreturncodeを主軸に行う。

    UiBatchCompileCheck.cs.tmpl の終了コード規約
    （0=成功／1=コンパイル失敗／2=テスト失敗／3=テスト未実施）に対応する。
    テスト失敗・テスト未実施のログには "error CS" という文字列が含まれないため、
    ログ正規表現だけに頼ると誤って成功と判定してしまう（修正前の不具合）。
    """

    def _run_with_returncode(self, returncode, log_text=None):
        def fake_run(command, timeout, check, stdout, stderr):
            log_file_path = command[command.index("-logFile") + 1]
            if log_text is not None:
                with open(log_file_path, "w", encoding="utf-8") as f:
                    f.write(log_text)
            return mock.Mock(returncode=returncode)

        with mock.patch.object(
            ubc,
            "determine_verification_stage",
            return_value=(ubc.STAGE_CLI, "/opt/unity/Unity", None),
        ), mock.patch.object(ubc.subprocess, "run", side_effect=fake_run) as mock_run:
            result = ubc.run_unity_batch_compile(
                "/dummy/project",
                execute_method="Sample.EditorTools.UiBatchCompileCheck.CompileAndTest",
            )
        return result, mock_run

    def test_returncode_0_is_success(self):
        result, mock_run = self._run_with_returncode(0, log_text="Compilation succeeded.\n")
        self.assertTrue(mock_run.called)
        self.assertEqual(result.stage, ubc.STAGE_CLI)
        self.assertTrue(result.success)
        self.assertIsNone(result.reason)

    def test_returncode_1_is_compile_failure(self):
        log = "Assets/Scripts/Foo.cs(1,1): error CS0103: The name 'Bar' does not exist\n"
        result, _ = self._run_with_returncode(1, log_text=log)
        self.assertEqual(result.stage, ubc.STAGE_CLI)
        self.assertFalse(result.success)
        self.assertEqual(result.reason, ubc.REASON_COMPILE_FAILED)
        self.assertTrue(result.errors)

    def test_returncode_2_is_test_failure_even_without_error_cs_in_log(self):
        # 不具合4の再現ケース：ログに "error CS" が無い（テスト失敗ログの実際の文言）
        log = "PlayModeテストが失敗した。失敗数: 1\n"
        result, _ = self._run_with_returncode(2, log_text=log)
        self.assertEqual(result.stage, ubc.STAGE_CLI)
        self.assertFalse(result.success)
        self.assertEqual(result.reason, ubc.REASON_TEST_FAILURE)

    def test_returncode_3_is_no_tests_executed_and_not_treated_as_success(self):
        # 不具合4の再現ケース：ログに "error CS" が無い（テスト未実施ログの実際の文言）
        log = "error: フィルタに一致するPlayModeテストが1件も無かった。テスト未実施として扱う。\n"
        result, _ = self._run_with_returncode(3, log_text=log)
        self.assertEqual(result.stage, ubc.STAGE_CLI)
        self.assertFalse(result.success)
        self.assertEqual(result.reason, ubc.REASON_NO_TESTS_EXECUTED)

    def test_unexpected_returncode_is_treated_as_failure(self):
        result, _ = self._run_with_returncode(99, log_text="")
        self.assertEqual(result.stage, ubc.STAGE_CLI)
        self.assertFalse(result.success)
        self.assertEqual(result.reason, ubc.REASON_UNEXPECTED_EXIT_CODE)


class MainArgumentParsingTest(unittest.TestCase):
    """--execute-method が既定値を持たず、必須引数として扱われることを検証する。"""

    def test_execute_method_is_required_argument(self):
        with self.assertRaises(SystemExit):
            ubc.main(["/dummy/project"])  # --execute-method 未指定


if __name__ == "__main__":
    unittest.main()
