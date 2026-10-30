"""验证创建并初始化工作流的 Manifest 入口与可转发提示词位置保持一致。"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (ROOT / "manifest.yml").read_text(encoding="utf-8")


class GroupAssetWorkflowPromptLocationTest(unittest.TestCase):
    def test_manifest_discovers_workflow_entrypoint_and_prompt_in_workflows(self):
        match = re.search(
            r"(?ms)^  - id: consumer\.group-asset-create-and-initialize\n(.*?)(?=^  - id: |\Z)",
            MANIFEST,
        )
        self.assertIsNotNone(match, "Manifest 必须注册创建并初始化工作流")
        capability = match.group(1)
        self.assertIn("kind: workflow", capability)
        self.assertIn("path: workflows/group-asset-repository", capability)
        self.assertIn("entrypoint: workflows/group-asset-repository/ENTRYPOINT.md", capability)
        self.assertTrue((ROOT / "workflows/group-asset-repository/ENTRYPOINT.md").is_file())
        self.assertTrue((ROOT / "workflows/group-asset-repository/WORKFLOW.md").is_file())
        self.assertTrue((ROOT / "workflows/group-asset-repository/CREATE_AND_INITIALIZE.md").is_file())
        self.assertFalse((ROOT / "harness/group-asset-repository/CREATE_AND_INITIALIZE.md").exists())

    def test_docs_link_to_the_workflow_directory(self):
        required_references = {
            "README.md": "workflows/group-asset-repository/CREATE_AND_INITIALIZE.md",
            "docs/architecture.md": "workflows/group-asset-repository/CREATE_AND_INITIALIZE.md",
            "docs/capability-and-harness-model.md": "workflows/group-asset-repository/ENTRYPOINT.md",
            "docs/group-asset-repository-bootstrap.md": "workflows/group-asset-repository/CREATE_AND_INITIALIZE.md",
            "docs/group-asset-repository-create-and-initialize.md": "workflows/group-asset-repository/CREATE_AND_INITIALIZE.md",
            "workflows/README.md": "group-asset-repository/CREATE_AND_INITIALIZE.md",
        }
        for relative, expected in required_references.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(document=relative):
                self.assertIn(expected, text)
                self.assertNotIn("harness/group-asset-repository/CREATE_AND_INITIALIZE.md", text)


if __name__ == "__main__":
    unittest.main()
