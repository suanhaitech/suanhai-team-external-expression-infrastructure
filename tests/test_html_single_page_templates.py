"""检查单页模板的结构契约和 Manifest 可发现性。"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SINGLE_PAGE = ROOT / "infrastructure/html/templates/single-page"
EXAMPLES = (
    ("cover", "editorial-v1", "cover"),
    ("agenda", "route-v1", "agenda"),
    ("transition", "statement-v1", "transition"),
    ("content", "evidence-v1", "content"),
    ("content", "method-v1", "content"),
    ("closing", "action-v1", "closing"),
    ("appendix", "source-register-v1", "appendix"),
)


class FragmentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.roots: list[tuple[str, dict[str, str | None]]] = []
        self.stack: list[str] = []
        self.void_tags = {"meta", "link", "img", "br", "hr", "input", "source"}

    def handle_starttag(self, tag: str, attrs) -> None:
        parsed_attrs = dict(attrs)
        self.tags.append((tag, parsed_attrs))
        if not self.stack:
            self.roots.append((tag, parsed_attrs))
        if tag not in self.void_tags:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.stack:
            index = len(self.stack) - 1 - self.stack[::-1].index(tag)
            del self.stack[index:]

    def handle_startendtag(self, tag: str, attrs) -> None:
        parsed_attrs = dict(attrs)
        self.tags.append((tag, parsed_attrs))
        if not self.stack:
            self.roots.append((tag, parsed_attrs))


class HtmlSinglePageTemplateTests(unittest.TestCase):
    def test_each_prototype_obeys_the_fragment_and_metadata_contract(self) -> None:
        self.assertEqual(len(EXAMPLES), 7)
        for role, variant, expected_role in EXAMPLES:
            with self.subTest(role=role, variant=variant):
                package = SINGLE_PAGE / role / variant
                metadata_path = package / "template.yml"
                page_path = package / "page.html"
                style_path = package / "styles.css"
                readme_path = package / "README.md"
                for path in (metadata_path, page_path, style_path, readme_path):
                    self.assertTrue(path.is_file(), path)

                metadata = metadata_path.read_text(encoding="utf-8")
                markup = page_path.read_text(encoding="utf-8")
                styles = style_path.read_text(encoding="utf-8")
                self.assertIn("kind: single-page-template", metadata)
                self.assertIn(f"role: {expected_role}", metadata)
                self.assertIn("offline: true", metadata)
                self.assertIn("network_dependencies: []", metadata)
                self.assertRegex(metadata, r"(?m)^id:\s*html\.single-page\.")
                self.assertIn("title_slot:", metadata)
                self.assertIn("page_number_slot: page-number", metadata)

                parser = FragmentParser()
                parser.feed(markup)
                self.assertEqual(len(parser.roots), 1, parser.roots)
                root_tag, root_attrs = parser.roots[0]
                self.assertEqual(root_tag, "section")
                self.assertEqual(root_attrs.get("data-single-page-role"), expected_role)
                self.assertNotRegex(markup.lower(), r"<(?:html|head|body|script|iframe)\b")
                self.assertNotRegex(markup + styles, r"https?://|url\(\s*['\"]?https?://")
                self.assertRegex(styles, r"(?m)^@(media|container)\s*\(max-width:")
                self.assertIn("@media print", styles)

                slot_block = re.search(r"(?ms)^slots:\s*\n((?:  - [^\n]+\n)+)", metadata)
                self.assertIsNotNone(slot_block)
                declared_slots = set(re.findall(r"(?m)^  - ([^\n]+)$", slot_block.group(1)))
                used_slots = set(re.findall(r'data-slot="([^"]+)"', markup))
                self.assertEqual(used_slots, declared_slots)

    def test_preview_catalog_covers_every_prototype(self) -> None:
        preview = (SINGLE_PAGE / "preview/preview.js").read_text(encoding="utf-8")
        for role, variant, _ in EXAMPLES:
            with self.subTest(role=role, variant=variant):
                self.assertIn(f'role: "{role}"', preview)
                self.assertIn(f'variant: "{variant}"', preview)

    def test_single_page_capabilities_are_registered(self) -> None:
        contract = (SINGLE_PAGE / "README.md").read_text(encoding="utf-8")
        research = (ROOT / "docs/html-single-page-template-sampling.md").read_text(encoding="utf-8")
        manifest = (ROOT / "manifest.yml").read_text(encoding="utf-8")
        self.assertIn("html.materialize", contract)
        self.assertIn("html.container.presentation-deck-v1", manifest)
        for role, variant, _ in EXAMPLES:
            package = SINGLE_PAGE / role / variant
            metadata = (package / "template.yml").read_text(encoding="utf-8")
            capability_id = re.search(r"(?m)^id:\s*(\S+)", metadata).group(1)
            self.assertIn(f"- id: {capability_id}", manifest)
        self.assertIn("已登记", research)


if __name__ == "__main__":
    unittest.main()
