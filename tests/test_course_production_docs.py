"""课程制作记录的引用闭合测试，防止样例与可调用资产逐渐脱节。"""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "infrastructure/html/examples/records"


def read_json(name: str) -> dict:
    return json.loads((RECORDS / name).read_text(encoding="utf-8"))


class CourseProductionRecordTest(unittest.TestCase):
    def test_page_plan_example_is_accepted_by_the_materializer_contract(self):
        path = ROOT / "infrastructure/html/tools/materialize/materialize_html.py"
        spec = importlib.util.spec_from_file_location("course_plan_example_reader", path)
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        plan = read_json("page-plan.json")
        self.assertEqual(tool.validate_page_plan(plan), plan)
        schema = json.loads((ROOT / "infrastructure/html/schemas/page-plan.schema.json").read_text(encoding="utf-8"))
        self.assertTrue(set(schema["required"]).issubset(plan))
        required_page_fields = set(schema["properties"]["pages"]["items"]["required"])
        for page in plan["pages"]:
            self.assertTrue(required_page_fields.issubset(page))

    def test_full_page_plan_has_closed_sources_and_backward_responses(self):
        plan = read_json("page-plan.json")
        self.assertEqual(plan["schema_version"], 1)
        sources = {source["id"]: source for source in plan["sources"]}
        self.assertEqual(len(sources), len(plan["sources"]))
        for source in sources.values():
            self.assertTrue((RECORDS / source["path"]).is_file())

        earlier_pages: set[str] = set()
        for page in plan["pages"]:
            self.assertNotIn(page["id"], earlier_pages)
            self.assertTrue(set(page["source_ids"]).issubset(sources))
            # 回扣必须有前文首次提出的问题，不允许仅按显示页码猜测关系。
            self.assertTrue(set(page["responds_to"]).issubset(earlier_pages))
            self.assertTrue(page["objective"].strip())
            self.assertTrue(page["core_message"].strip())
            earlier_pages.add(page["id"])

    def test_example_templates_and_slots_are_real_assets(self):
        templates = {}
        for metadata in (ROOT / "infrastructure/html/templates/single-page").rglob("template.yml"):
            text = metadata.read_text(encoding="utf-8")
            match = re.search(r"^id:\s*(\S+)\s*$", text, re.MULTILINE)
            if match:
                templates[match.group(1)] = metadata

        for page in read_json("page-plan.json")["pages"]:
            metadata = templates[page["template_id"]]
            html = (metadata.parent / "page.html").read_text(encoding="utf-8")
            declared_slots = set(re.findall(r'data-slot="([^"]+)"', html))
            self.assertTrue(set(page["slots"]).issubset(declared_slots), page["id"])
            self.assertTrue(all(isinstance(value, str) for value in page["slots"].values()))

    def test_source_map_covers_all_pages_and_locators_exist(self):
        plan = read_json("page-plan.json")
        source_map = read_json("source-map.json")
        page_ids = {page["id"] for page in plan["pages"]}
        mapped_pages = {page["page_id"] for page in source_map["pages"]}
        self.assertEqual(page_ids, mapped_pages)
        self.assertEqual(len(mapped_pages), len(source_map["pages"]))
        sources = {source["id"]: source for source in source_map["sources"]}
        self.assertEqual(set(sources), {source["id"] for source in plan["sources"]})
        for page in source_map["pages"]:
            self.assertTrue(page["claims"])
            for claim in page["claims"]:
                self.assertTrue(set(claim["source_ids"]).issubset(sources))
                for source_id in claim["source_ids"]:
                    text = (RECORDS / sources[source_id]["path"]).read_text(encoding="utf-8")
                    self.assertIn("## " + claim["locator"], text)

    def test_revision_partitions_full_plan_without_fabricated_approval(self):
        page_ids = {page["id"] for page in read_json("page-plan.json")["pages"]}
        revision = read_json("revision.json")
        target = set(revision["target_page_ids"])
        protected = set(revision["protected_page_ids"])
        self.assertFalse(target & protected)
        self.assertEqual(target | protected, page_ids)
        self.assertTrue((RECORDS / revision["page_plan"]).is_file())
        self.assertIsNone(revision["user_confirmation"])
        self.assertIsNone(revision["feedback_event_reference"])
        self.assertEqual(set(revision["verification"].values()), {"not-run"})
        self.assertIsNone(read_json("brief.json")["user_confirmation"])

    def test_qa_example_cannot_claim_a_completed_check(self):
        qa = read_json("qa.json")
        schema = json.loads((ROOT / "infrastructure/html/schemas/check-result.schema.json").read_text(encoding="utf-8"))
        self.assertTrue(set(schema["required"]).issubset(qa))
        self.assertIsNone(qa["html_sha256"])
        self.assertEqual(qa["status"], "not-run")
        self.assertTrue(qa["checks"])
        for check in qa["checks"]:
            self.assertEqual(check["status"], "not-run")
            self.assertTrue(check["evidence"]["example"])
            self.assertTrue(check["evidence"]["reason"])

    def test_modified_documentation_has_resolvable_local_links(self):
        docs = [
            ROOT / "scenarios/course-learning-v1/README.md",
            ROOT / "workflows/html/production/WORKFLOW.md",
            ROOT / "workflows/html/production/ENTRYPOINT.md",
            ROOT / "workflows/task-loop/ENTRYPOINT.md",
            ROOT / "docs/course-reusable-assets.md",
            RECORDS / "README.md",
        ]
        for doc in docs:
            for link in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
                if "://" in link or link.startswith("#"):
                    continue
                target = link.split("#", 1)[0]
                self.assertTrue((doc.parent / target).resolve().exists(), f"{doc}: {link}")


if __name__ == "__main__":
    unittest.main()
