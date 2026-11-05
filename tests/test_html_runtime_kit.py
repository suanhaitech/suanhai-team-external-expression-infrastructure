"""HTML 页面运行时包的离线资源、元数据和行为契约测试。"""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path
from pathlib import PurePosixPath
import re
import shutil
import subprocess
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
KIT = REPO_ROOT / "infrastructure/html/runtime-kits/runtime-kit-v1"
PACKAGE = KIT / "package.yml"
CATALOG = KIT / "index.yml"
RUNTIME_JS = KIT / "runtime.js"

_MATERIALIZE_PATH = REPO_ROOT / "infrastructure/html/tools/materialize/materialize_html.py"
_MATERIALIZE_SPEC = importlib.util.spec_from_file_location("html_materialize_runtime_test", _MATERIALIZE_PATH)
assert _MATERIALIZE_SPEC and _MATERIALIZE_SPEC.loader
_MATERIALIZE = importlib.util.module_from_spec(_MATERIALIZE_SPEC)
_MATERIALIZE_SPEC.loader.exec_module(_MATERIALIZE)


def scalar_metadata(path: Path) -> dict[str, str]:
    """读取运行时包的扁平 YAML 元数据，避免测试依赖额外 YAML 库。"""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


class HtmlRuntimeKitContractTest(unittest.TestCase):
    def test_package_metadata_and_catalog_are_consistent(self):
        package = scalar_metadata(PACKAGE)
        package_text = PACKAGE.read_text(encoding="utf-8")
        catalog_text = CATALOG.read_text(encoding="utf-8")
        self.assertEqual(package["id"], "html.runtime-kit-v1")
        self.assertEqual(package["kind"], "runtime-kit")
        self.assertEqual(package["version"], "1.1.1")
        self.assertEqual(package["offline"], "true")
        self.assertIn("name: KaTeX", package_text)
        self.assertIn("id: html.runtime-kit-v1", catalog_text)
        self.assertIn("id: math-rendering", catalog_text)
        self.assertIn("id: display-mode-controls", catalog_text)
        self.assertIn("id: print-control", catalog_text)
        self.assertIn("id: fullscreen-control", catalog_text)

    def test_all_declared_runtime_resources_are_local_files(self):
        package_text = PACKAGE.read_text(encoding="utf-8")
        declared = re.findall(r"^\s+- (.+)$", package_text, flags=re.MULTILINE)
        for relative in ("runtime.css", "math/katex.min.css", "math/katex.min.js", "runtime.js"):
            self.assertIn(relative, declared)
            self.assertTrue((KIT / relative).is_file(), relative)
        self.assertTrue((KIT / "math/LICENSE").is_file())
        fonts = list((KIT / "math/fonts").glob("*.woff2"))
        self.assertGreater(len(fonts), 0)
        self.assertNotRegex(package_text, r"https?://|//cdn")
        for path in [KIT / "runtime.css", KIT / "runtime.js", KIT / "math/katex.min.css"]:
            text = path.read_text(encoding="utf-8", errors="ignore")
            self.assertNotRegex(text, r"(?:src|href|url\()\s*[=:]?\s*[\"']?https?://|//cdn")

    def test_runtime_script_declares_formula_modes_print_and_idempotence(self):
        source = RUNTIME_JS.read_text(encoding="utf-8")
        for marker in (
            "data-math",
            "data-math-display",
            "window.katex",
            "data-runtime-mode",
            "data-layout-mode",
            "window.print()",
            "data-runtime-ready",
            "data-math-fallback",
            "data-runtime-fullscreen",
            "data-runtime-pdf",
            "requestFullscreen",
            "exitFullscreen",
            "fullscreenchange",
            "data-runtime-mode-select",
            "选择页面显示模式",
        ):
            self.assertIn(marker, source)
        self.assertIn('["自动", "auto"]', source)
        self.assertIn('["窄屏", "narrow"]', source)
        self.assertIn('["平板", "tablet"]', source)
        self.assertIn('["桌面", "desktop"]', source)
        self.assertIn('throwOnError: true', source)
        self.assertIn('trust: false', source)
        self.assertIn("保存 PDF", source)
        self.assertIn("全屏", source)

    def test_print_styles_hide_toolbar_and_template_exposes_runtime_slots(self):
        css = (KIT / "runtime.css").read_text(encoding="utf-8")
        report_css = (REPO_ROOT / "infrastructure/html/templates/presets/project-report-v1/report.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"@media\s+print[\s\S]*?\[data-runtime-toolbar\][\s\S]*?display:\s*none")
        self.assertIn(".runtime-toolbar__mode-buttons", css)
        self.assertIn("min-height: 44px", css)
        self.assertIn(".runtime-status", css)
        # 小屏文字可发现性和控件边界由真实浏览器回归检查。
        self.assertNotIn(".report-grid", css)
        self.assertIn('html[data-layout-mode="narrow"] .report-grid > *', report_css)
        self.assertIn('grid-column: 1 / -1', report_css)
        template = (REPO_ROOT / "infrastructure/html/templates/presets/project-report-v1/index.html").read_text(encoding="utf-8")
        for marker in (
            "<!-- SUANHAI_RUNTIME_STYLESHEETS -->",
            "<!-- SUANHAI_RUNTIME_TOOLBAR -->",
            "<!-- SUANHAI_RUNTIME_SCRIPTS -->",
        ):
            self.assertEqual(template.count(marker), 1, marker)
        self.assertIn("overflow-wrap: anywhere", report_css)

    def test_runtime_is_optional_for_legacy_templates_without_runtime_slots(self):
        legacy = [(PurePosixPath("index.html"), b"<html><body>legacy</body></html>")]
        result = _MATERIALIZE.inject_runtime_kit(legacy, None)
        self.assertEqual(result, legacy)

        marked = [(PurePosixPath("index.html"), (
            "<!-- SUANHAI_RUNTIME_STYLESHEETS -->"
            "<!-- SUANHAI_RUNTIME_TOOLBAR -->"
            "<!-- SUANHAI_RUNTIME_SCRIPTS -->"
        ).encode("utf-8"))]
        result = _MATERIALIZE.inject_runtime_kit(marked, None)
        self.assertEqual(result[0][1], b"")

        with self.assertRaises(_MATERIALIZE.MaterializeError):
            _MATERIALIZE.inject_runtime_kit(legacy, {"id": "html.runtime-kit-v1"})

    def test_materializer_rejects_runtime_package_missing_fixed_entrypoints(self):
        with self.assertRaisesRegex(_MATERIALIZE.MaterializeError, "math/katex.min.js"):
            _MATERIALIZE.validate_runtime_files([
                (PurePosixPath("runtime.css"), b""),
                (PurePosixPath("runtime.js"), b""),
                (PurePosixPath("math/katex.min.css"), b""),
            ])

    def test_optional_node_syntax_check(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("测试机未安装 Node.js；静态契约仍由其他测试覆盖")
        result = subprocess.run(
            [node, "--check", str(RUNTIME_JS)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
