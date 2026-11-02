"""验证创建并初始化工作流的 Manifest 入口与可转发提示词位置保持一致。"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (ROOT / "manifest.yml").read_text(encoding="utf-8")
CREATE_PROMPT = (ROOT / "workflows/group-asset-repository-create-and-initialize/CREATE_AND_INITIALIZE.md").read_text(encoding="utf-8")
CREATE_ENTRYPOINT = (ROOT / "workflows/group-asset-repository-create-and-initialize/ENTRYPOINT.md").read_text(encoding="utf-8")


class GroupAssetWorkflowPromptLocationTest(unittest.TestCase):
    def test_manifest_discovers_workflow_entrypoint_and_prompt_in_workflows(self):
        match = re.search(
            r"(?ms)^  - id: consumer\.group-asset-create-and-initialize\n(.*?)(?=^  - id: |\Z)",
            MANIFEST,
        )
        self.assertIsNotNone(match, "Manifest 必须注册创建并初始化工作流")
        capability = match.group(1)
        self.assertIn("kind: workflow", capability)
        workflow_path = "workflows/group-asset-repository-create-and-initialize"
        self.assertIn(f"path: {workflow_path}", capability)
        self.assertIn(f"entrypoint: {workflow_path}/ENTRYPOINT.md", capability)
        self.assertTrue((ROOT / workflow_path / "ENTRYPOINT.md").is_file())
        self.assertTrue((ROOT / workflow_path / "WORKFLOW.md").is_file())
        self.assertTrue((ROOT / workflow_path / "CREATE_AND_INITIALIZE.md").is_file())

        onboarding = re.search(
            r"(?ms)^  - id: consumer\.group-asset-onboarding\n(.*?)(?=^  - id: |\Z)",
            MANIFEST,
        )
        self.assertIsNotNone(onboarding, "Manifest 必须注册独立的小组上下文初始化工作流")
        self.assertIn("path: workflows/group-asset-repository-onboarding", onboarding.group(1))
        self.assertTrue((ROOT / "workflows/group-asset-repository-onboarding/ENTRYPOINT.md").is_file())

        self.assertTrue((ROOT / "infrastructure/group-asset-repository/tools/bootstrap/materialize_template.py").is_file())
        self.assertTrue((ROOT / "infrastructure/group-asset-repository/templates/group-asset-repository-v1/AGENTS.md").is_file())

    def test_docs_link_to_the_workflow_directory(self):
        required_references = {
            "README.md": "workflows/group-asset-repository-create-and-initialize/CREATE_AND_INITIALIZE.md",
            "docs/architecture.md": "workflows/group-asset-repository-create-and-initialize/CREATE_AND_INITIALIZE.md",
            "docs/capability-and-harness-model.md": "workflows/group-asset-repository-create-and-initialize/ENTRYPOINT.md",
            "docs/group-asset-repository-bootstrap.md": "workflows/group-asset-repository-create-and-initialize/CREATE_AND_INITIALIZE.md",
            "docs/group-asset-repository-create-and-initialize.md": "workflows/group-asset-repository-create-and-initialize/CREATE_AND_INITIALIZE.md",
            "workflows/README.md": "group-asset-repository-create-and-initialize/CREATE_AND_INITIALIZE.md",
        }
        for relative, expected in required_references.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(document=relative):
                self.assertIn(expected, text)
                self.assertNotIn("workflows/group-asset-repository/CREATE_AND_INITIALIZE.md", text)

    def test_create_flow_reuses_first_submodule_preflight_snapshot(self):
        self.assertIn("新仓建立后的首个共享能力快照", CREATE_PROMPT)
        self.assertIn("把阶段 4 的预检快照和锁定 SHA 交给 onboarding 入口复用", CREATE_PROMPT)
        self.assertIn("远端 `main` 与模板 gitlink 的 SHA 不同", CREATE_PROMPT)
        self.assertIn("本地检查通过可在固定版本上继续", CREATE_PROMPT)
        self.assertIn("将这次预检快照和固定 SHA 传给", CREATE_ENTRYPOINT)


if __name__ == "__main__":
    unittest.main()
