"""lint_ugui_csharp.py の単体テスト。

requirements.md 7.3節末尾に定義された8種の禁止パターンについて、
検出する正例・検出しない負例をそれぞれ用意する。
標準ライブラリの unittest のみを使用する（追加パッケージ不要）。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "skills"
    / "unity-ugui-runtime-ui"
    / "scripts"
    / "lint_ugui_csharp.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("lint_ugui_csharp", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # dataclasses looks up sys.modules[cls.__module__] during class creation,
    # so the module must be registered before exec_module runs.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LintUguiCSharpTestCase(unittest.TestCase):
    """個々のルールをモジュール関数経由で検証する基底クラス。"""

    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.tmpdir_path = Path(cls.tmpdir.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def _write_cs(self, name: str, content: str) -> Path:
        path = self.tmpdir_path / name
        path.write_text(content, encoding="utf-8")
        return path

    def _rule_ids(self, path: Path) -> set:
        violations = self.module.lint_paths([str(path)])
        return {v.rule_id for v in violations}


class UnityEditorNamespaceTests(LintUguiCSharpTestCase):
    def test_detects_using_unity_editor(self):
        path = self._write_cs(
            "editor_ref_bad.cs",
            "using UnityEditor;\n\npublic class Foo {}\n",
        )
        self.assertIn("unity_editor_namespace", self._rule_ids(path))

    def test_detects_qualified_unity_editor_usage(self):
        path = self._write_cs(
            "editor_ref_bad2.cs",
            "public class Foo {\n"
            "    void Bar() { UnityEditor.AssetDatabase.Refresh(); }\n"
            "}\n",
        )
        self.assertIn("unity_editor_namespace", self._rule_ids(path))

    def test_does_not_flag_similar_identifier(self):
        # クラス名の一部に紛れ込んだ文字列であって、独立した単語ではないため
        # 誤検出してはならない（単語境界での判定を確認する負例）。
        path = self._write_cs(
            "editor_ref_ok.cs",
            "using UnityEngine;\n\n"
            "public class MyUnityEditorHelperUnrelated {\n"
            "    void Bar() { var x = 1; }\n"
            "}\n",
        )
        self.assertNotIn("unity_editor_namespace", self._rule_ids(path))


class OnGuiDefinitionTests(LintUguiCSharpTestCase):
    def test_detects_ongui_definition(self):
        path = self._write_cs(
            "ongui_bad.cs",
            "public class Foo {\n"
            "    void OnGUI() { }\n"
            "}\n",
        )
        self.assertIn("ongui_definition", self._rule_ids(path))

    def test_does_not_flag_method_with_ongui_prefix_name(self):
        path = self._write_cs(
            "ongui_ok.cs",
            "public class Foo {\n"
            "    void OnGUIStyleSetup() { }\n"
            "}\n",
        )
        self.assertNotIn("ongui_definition", self._rule_ids(path))


class AssetDatabaseUsageTests(LintUguiCSharpTestCase):
    def test_detects_asset_database(self):
        path = self._write_cs(
            "assetdb_bad.cs",
            "public class Foo {\n"
            "    void Bar() { AssetDatabase.Refresh(); }\n"
            "}\n",
        )
        self.assertIn("asset_database_usage", self._rule_ids(path))

    def test_detects_get_builtin_extra_resource(self):
        path = self._write_cs(
            "builtin_bad.cs",
            "public class Foo {\n"
            "    void Bar() {\n"
            "        var sp = Resources.GetBuiltinExtraResource<Sprite>(\"UI/Skin/Background.psd\");\n"
            "    }\n"
            "}\n",
        )
        self.assertIn("asset_database_usage", self._rule_ids(path))

    def test_does_not_flag_unrelated_code(self):
        path = self._write_cs(
            "assetdb_ok.cs",
            "public class Foo {\n"
            "    void Bar() { var x = Resources.Load<Sprite>(\"UI/x\"); }\n"
            "}\n",
        )
        self.assertNotIn("asset_database_usage", self._rule_ids(path))


class FindReacquisitionTests(LintUguiCSharpTestCase):
    def test_detects_game_object_find(self):
        path = self._write_cs(
            "find_bad1.cs",
            "public class Foo {\n"
            "    void Bar() { var go = GameObject.Find(\"Panel\"); }\n"
            "}\n",
        )
        self.assertIn("find_reacquisition", self._rule_ids(path))

    def test_detects_transform_find(self):
        path = self._write_cs(
            "find_bad2.cs",
            "public class Foo {\n"
            "    void Bar() { var t = transform.Find(\"Child\"); }\n"
            "}\n",
        )
        self.assertIn("find_reacquisition", self._rule_ids(path))

    def test_does_not_flag_list_find(self):
        path = self._write_cs(
            "find_ok.cs",
            "using System.Collections.Generic;\n"
            "public class Foo {\n"
            "    void Bar(List<int> items) { var x = items.Find(i => i > 0); }\n"
            "    void Baz(UnityEngine.Transform childTransform) {\n"
            "        var y = childTransform.Find(\"X\");\n"
            "    }\n"
            "}\n",
        )
        self.assertNotIn("find_reacquisition", self._rule_ids(path))


class LayoutGroupContentSizeFitterTests(LintUguiCSharpTestCase):
    def test_detects_content_size_fitter_on_layout_group_child(self):
        path = self._write_cs(
            "layout_child_bad.cs",
            "public class Foo {\n"
            "    void Bar(GameObject panel) {\n"
            "        panel.AddComponent<VerticalLayoutGroup>();\n"
            "        var child = new GameObject(\"Child\");\n"
            "        child.transform.SetParent(panel.transform, false);\n"
            "        child.AddComponent<ContentSizeFitter>();\n"
            "    }\n"
            "}\n",
        )
        self.assertIn(
            "layout_group_child_content_size_fitter", self._rule_ids(path)
        )

    def test_does_not_flag_content_size_fitter_on_layout_group_object_itself(self):
        path = self._write_cs(
            "layout_child_ok.cs",
            "public class Foo {\n"
            "    void Bar() {\n"
            "        var content = new GameObject(\"Content\");\n"
            "        content.AddComponent<VerticalLayoutGroup>();\n"
            "        content.AddComponent<ContentSizeFitter>();\n"
            "    }\n"
            "}\n",
        )
        self.assertNotIn(
            "layout_group_child_content_size_fitter", self._rule_ids(path)
        )

    def test_detects_content_size_fitter_on_typeof_layout_group_child(self):
        # 不具合1：UiFactory.cs.tmpl と同じ new GameObject(..., typeof(...), ...)
        # 方式でLayoutGroupが付与された親オブジェクトの子に、別途
        # ContentSizeFitterが付与されている場合を検出できなければならない。
        path = self._write_cs(
            "layout_child_typeof_bad.cs",
            "public class Foo {\n"
            "    void Bar() {\n"
            "        var panelGo = new GameObject(\"Panel\", typeof(RectTransform), typeof(VerticalLayoutGroup));\n"
            "        var childGo = new GameObject(\"Child\", typeof(RectTransform));\n"
            "        childGo.transform.SetParent(panelGo.transform, false);\n"
            "        childGo.AddComponent<ContentSizeFitter>();\n"
            "    }\n"
            "}\n",
        )
        self.assertIn(
            "layout_group_child_content_size_fitter", self._rule_ids(path)
        )

    def test_detects_content_size_fitter_via_direct_set_parent_without_transform(self):
        # 不具合1：UiFactory.cs.tmpl は rect.SetParent(parent, false) のように
        # .transform を介さず直接 SetParent を呼ぶ。この形の親子付けでも
        # LayoutGroupの子へのContentSizeFitter付与を検出できなければならない。
        path = self._write_cs(
            "layout_child_direct_setparent_bad.cs",
            "public class Foo {\n"
            "    void Bar(RectTransform panel, RectTransform child) {\n"
            "        panel.AddComponent<VerticalLayoutGroup>();\n"
            "        child.SetParent(panel, false);\n"
            "        child.AddComponent<ContentSizeFitter>();\n"
            "    }\n"
            "}\n",
        )
        self.assertIn(
            "layout_group_child_content_size_fitter", self._rule_ids(path)
        )

    def test_does_not_flag_typeof_content_size_fitter_on_same_object(self):
        # UiFactory.cs.tmpl の ScrollRect Content 相当：LayoutGroup と
        # ContentSizeFitter を同一の new GameObject(...) 呼び出しでtypeof列挙して
        # いる場合（自分自身への付与）は許容する。
        path = self._write_cs(
            "layout_child_typeof_ok.cs",
            "public class Foo {\n"
            "    void Bar(RectTransform parent) {\n"
            "        var contentGo = new GameObject(\"Content\", typeof(RectTransform), typeof(VerticalLayoutGroup), typeof(ContentSizeFitter));\n"
            "        var contentRect = (RectTransform)contentGo.transform;\n"
            "        contentRect.SetParent(parent, false);\n"
            "    }\n"
            "}\n",
        )
        self.assertNotIn(
            "layout_group_child_content_size_fitter", self._rule_ids(path)
        )


class RawColorLiteralColorClearAndUiThemeTests(LintUguiCSharpTestCase):
    def test_does_not_flag_color_clear(self):
        # 不具合2：Color.clear はマスク描画専用の透明色であり、UiThemeに集約する
        # 対象の「配色」ではないため raw_color_literal の対象外とする。
        path = self._write_cs(
            "color_clear_ok.cs",
            "public class Foo {\n"
            "    void Bar(Image viewportImage) {\n"
            "        viewportImage.color = Color.clear;\n"
            "    }\n"
            "}\n",
        )
        self.assertNotIn("raw_color_literal", self._rule_ids(path))

    def test_does_not_flag_color32_literal_inside_uitheme_class(self):
        # 不具合2：UiTheme自身（色の集約先）がColor32定数を定義する行は
        # raw_color_literal の対象外とする。
        path = self._write_cs(
            "uitheme_colors_ok.cs",
            "namespace App.Ui {\n"
            "    public static class UiTheme {\n"
            "        public static class Colors {\n"
            "            public static readonly Color32 Accent = new Color32(0x4D, 0xA3, 0xFF, 0xFF);\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        self.assertNotIn("raw_color_literal", self._rule_ids(path))

    def test_does_not_flag_color32_derived_from_existing_color_components(self):
        # 不具合2：CreateNineSliceSprite の
        # new Color32(fillColor.r, fillColor.g, fillColor.b, 0) は既存Colorの
        # 成分から派生した値（不透明度のみ変更）であり、新規の色リテラル導入では
        # ないため対象外とする。
        path = self._write_cs(
            "color32_derived_ok.cs",
            "public class Foo {\n"
            "    Color32 Bar(Color32 fillColor) {\n"
            "        return new Color32(fillColor.r, fillColor.g, fillColor.b, 0);\n"
            "    }\n"
            "}\n",
        )
        self.assertNotIn("raw_color_literal", self._rule_ids(path))

    def test_still_flags_color32_literal_outside_uitheme_class(self):
        # 除外が過度に緩くなっていないことの回帰テスト：UiTheme以外のクラスでの
        # 色リテラル直書きは引き続き検出されなければならない。
        path = self._write_cs(
            "non_uitheme_colors_bad.cs",
            "namespace App.Ui {\n"
            "    public static class ScreenPalette {\n"
            "        public static readonly Color32 Accent = new Color32(0x4D, 0xA3, 0xFF, 0xFF);\n"
            "    }\n"
            "}\n",
        )
        self.assertIn("raw_color_literal", self._rule_ids(path))


class CommentLineExclusionTests(LintUguiCSharpTestCase):
    def test_does_not_flag_unity_editor_mentioned_only_in_comment(self):
        # 不具合3：UnityEditor は実行時コードでは参照しない旨を説明する日本語コメント
        # 自体が誤検出されてはならない。
        path = self._write_cs(
            "comment_unity_editor_ok.cs",
            "public class Foo {\n"
            "    // UnityEditor 名前空間・OnGUI・AssetDatabase は参照しない\n"
            "    void Bar() { var x = 1; }\n"
            "}\n",
        )
        self.assertNotIn("unity_editor_namespace", self._rule_ids(path))
        self.assertNotIn("asset_database_usage", self._rule_ids(path))

    def test_still_flags_unity_editor_usage_outside_comment(self):
        # 回帰テスト：コメント除去がコード本体の検出まで消してしまわないこと。
        path = self._write_cs(
            "comment_unity_editor_bad.cs",
            "using UnityEditor; // これはコメントではなく実コード\n"
            "public class Foo {}\n",
        )
        self.assertIn("unity_editor_namespace", self._rule_ids(path))


class EventSystemMissingTests(LintUguiCSharpTestCase):
    def test_detects_missing_event_system_when_canvas_created(self):
        path = self._write_cs(
            "eventsystem_bad.cs",
            "public class Foo {\n"
            "    void Bar(GameObject root) {\n"
            "        root.AddComponent<Canvas>();\n"
            "    }\n"
            "}\n",
        )
        self.assertIn("event_system_missing", self._rule_ids(path))

    def test_does_not_flag_when_event_system_created(self):
        path = self._write_cs(
            "eventsystem_ok.cs",
            "public class Foo {\n"
            "    void Bar(GameObject root, GameObject es) {\n"
            "        root.AddComponent<Canvas>();\n"
            "        es.AddComponent<EventSystem>();\n"
            "    }\n"
            "}\n",
        )
        self.assertNotIn("event_system_missing", self._rule_ids(path))

    def test_does_not_flag_when_no_canvas_created(self):
        path = self._write_cs(
            "eventsystem_irrelevant.cs",
            "public class Foo {\n"
            "    void Bar() { var x = 1; }\n"
            "}\n",
        )
        self.assertNotIn("event_system_missing", self._rule_ids(path))

    def test_detects_missing_event_system_when_canvas_created_via_typeof(self):
        # UiFactory.cs.tmpl 由来のパターン：AddComponent<T>() ではなく
        # new GameObject(name, typeof(Canvas), ...) というコンストラクタ列挙で
        # Canvasを付与する構成。この方式でもEventSystem欠落を検出できなければ
        # ならない（不具合1：偽陰性の回帰テスト）。
        path = self._write_cs(
            "eventsystem_typeof_bad.cs",
            "public class Foo {\n"
            "    void Bar(string name) {\n"
            "        var go = new GameObject(name, typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler));\n"
            "    }\n"
            "}\n",
        )
        self.assertIn("event_system_missing", self._rule_ids(path))

    def test_does_not_flag_when_event_system_created_via_typeof(self):
        path = self._write_cs(
            "eventsystem_typeof_ok.cs",
            "public class Foo {\n"
            "    void Bar(string name) {\n"
            "        var go = new GameObject(name, typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler));\n"
            "        var es = new GameObject(\"EventSystem\", typeof(EventSystem), typeof(StandaloneInputModule));\n"
            "    }\n"
            "}\n",
        )
        self.assertNotIn("event_system_missing", self._rule_ids(path))


class CanvasScalerMissingTests(LintUguiCSharpTestCase):
    def test_detects_missing_canvas_scaler(self):
        path = self._write_cs(
            "canvasscaler_bad.cs",
            "public class Foo {\n"
            "    void Bar(GameObject root) {\n"
            "        root.AddComponent<Canvas>();\n"
            "    }\n"
            "}\n",
        )
        self.assertIn("canvas_scaler_missing", self._rule_ids(path))

    def test_does_not_flag_when_canvas_scaler_present(self):
        path = self._write_cs(
            "canvasscaler_ok.cs",
            "public class Foo {\n"
            "    void Bar(GameObject root) {\n"
            "        root.AddComponent<Canvas>();\n"
            "        root.AddComponent<CanvasScaler>();\n"
            "    }\n"
            "}\n",
        )
        self.assertNotIn("canvas_scaler_missing", self._rule_ids(path))

    def test_detects_missing_canvas_scaler_via_typeof(self):
        # 不具合1：typeof(Canvas) はあるが typeof(CanvasScaler) が無い構成。
        path = self._write_cs(
            "canvasscaler_typeof_bad.cs",
            "public class Foo {\n"
            "    void Bar(string name) {\n"
            "        var go = new GameObject(name, typeof(RectTransform), typeof(Canvas));\n"
            "    }\n"
            "}\n",
        )
        self.assertIn("canvas_scaler_missing", self._rule_ids(path))

    def test_does_not_flag_when_canvas_scaler_present_via_typeof(self):
        path = self._write_cs(
            "canvasscaler_typeof_ok.cs",
            "public class Foo {\n"
            "    void Bar(string name) {\n"
            "        var go = new GameObject(name, typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));\n"
            "    }\n"
            "}\n",
        )
        self.assertNotIn("canvas_scaler_missing", self._rule_ids(path))


class RawColorLiteralTests(LintUguiCSharpTestCase):
    def test_detects_new_color_literal(self):
        path = self._write_cs(
            "color_bad1.cs",
            "public class Foo {\n"
            "    void Bar() { var c = new Color(1f, 0f, 0f, 1f); }\n"
            "}\n",
        )
        self.assertIn("raw_color_literal", self._rule_ids(path))

    def test_detects_named_color_literal(self):
        path = self._write_cs(
            "color_bad2.cs",
            "public class Foo {\n"
            "    void Bar() { var c = Color.red; }\n"
            "}\n",
        )
        self.assertIn("raw_color_literal", self._rule_ids(path))

    def test_does_not_flag_theme_reference(self):
        path = self._write_cs(
            "color_ok.cs",
            "public class Foo {\n"
            "    void Bar() { var c = UiTheme.Colors.Primary; }\n"
            "}\n",
        )
        self.assertNotIn("raw_color_literal", self._rule_ids(path))


class CleanFileTests(LintUguiCSharpTestCase):
    def test_clean_file_reports_no_violations(self):
        path = self._write_cs(
            "clean_screen.cs",
            "using UnityEngine;\n"
            "using UnityEngine.UI;\n"
            "using UnityEngine.EventSystems;\n\n"
            "public class SampleScreen : MonoBehaviour {\n"
            "    private Button _closeButton;\n\n"
            "    public void Build(GameObject root, GameObject eventSystemHost) {\n"
            "        var canvas = root.AddComponent<Canvas>();\n"
            "        root.AddComponent<CanvasScaler>();\n"
            "        root.AddComponent<GraphicRaycaster>();\n"
            "        eventSystemHost.AddComponent<EventSystem>();\n\n"
            "        var content = new GameObject(\"Content\");\n"
            "        content.AddComponent<VerticalLayoutGroup>();\n"
            "        content.AddComponent<ContentSizeFitter>();\n\n"
            "        _closeButton = content.AddComponent<Button>();\n"
            "        var image = _closeButton.GetComponent<Image>();\n"
            "        image.color = UiTheme.Colors.Primary;\n"
            "    }\n"
            "}\n",
        )
        self.assertEqual(self._rule_ids(path), set())


class CliIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write_cs(self, name: str, content: str) -> Path:
        path = self.tmpdir_path / name
        path.write_text(content, encoding="utf-8")
        return path

    def _run_cli(self, *args: str):
        return subprocess.run(
            [sys.executable, str(MODULE_PATH), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_cli_exits_nonzero_when_violation_found(self):
        path = self._write_cs(
            "cli_bad.cs",
            "using UnityEditor;\npublic class Foo {}\n",
        )
        result = self._run_cli(str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unity_editor_namespace", result.stdout)

    def test_cli_exits_zero_when_clean(self):
        path = self._write_cs(
            "cli_ok.cs",
            "using UnityEngine;\npublic class Foo {}\n",
        )
        result = self._run_cli(str(path))
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
