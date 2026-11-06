"""既有仓库接入协议的静态契约检查。

这些断言覆盖接入流程最容易因文档改动而丢失的工程边界：工作流已注册、
提示词按不可变提交读取入口、必须保留消费端规则、版本更新不自动漂移，
以及未提交 gitlink 时不伪称完整预检通过。
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (ROOT / "manifest.yml").read_text(encoding="utf-8")
ENTRYPOINT = (ROOT / "workflows/infrastructure-adoption/ENTRYPOINT.md").read_text(encoding="utf-8")
WORKFLOW = (ROOT / "workflows/infrastructure-adoption/WORKFLOW.md").read_text(encoding="utf-8")
PROMPT = (ROOT / "workflows/infrastructure-adoption/ADOPT_EXISTING_REPOSITORY.md").read_text(encoding="utf-8")
INSTALLER = (ROOT / "infrastructure/repository-management/tools/infrastructure-adoption-harness/install_harness.py").read_text(encoding="utf-8")
TEMPLATE_HARNESS = (ROOT / "infrastructure/group-asset-repository/templates/group-asset-repository-v1/AGENTS.md").read_text(encoding="utf-8")
BOOTSTRAP = (ROOT / "docs/consumer-repository-bootstrap.md").read_text(encoding="utf-8")
HARNESS_PROTOCOL = (ROOT / "docs/consumer-repository-harness-v0.1.md").read_text(encoding="utf-8")
VERSIONING = (ROOT / "docs/submodule-consumer-versioning.md").read_text(encoding="utf-8")
SUBMODULE_UPDATE = (ROOT / "workflows/submodule-update/ENTRYPOINT.md").read_text(encoding="utf-8")
SUBMODULE_UPDATE_WORKFLOW = (ROOT / "workflows/submodule-update/WORKFLOW.md").read_text(encoding="utf-8")
ONBOARDING = (ROOT / "workflows/group-asset-repository-onboarding/ENTRYPOINT.md").read_text(encoding="utf-8")
TASK_LOOP = (ROOT / "workflows/task-loop/ENTRYPOINT.md").read_text(encoding="utf-8")
HTML_PRODUCTION = (ROOT / "workflows/html/production/ENTRYPOINT.md").read_text(encoding="utf-8")
SUBMODULE_UPDATE_WORKFLOW = (ROOT / "workflows/submodule-update/WORKFLOW.md").read_text(encoding="utf-8")
SUBMODULE_UPDATE_ENTRYPOINT = (ROOT / "workflows/submodule-update/ENTRYPOINT.md").read_text(encoding="utf-8")


class InfrastructureAdoptionDocsTest(unittest.TestCase):
    def test_manifest_registers_workflow_and_harness_tool_dependency(self):
        match = re.search(
            r"(?ms)^  - id: consumer\.infrastructure-adoption\n(.*?)(?=^  - id: |\Z)",
            MANIFEST,
        )
        self.assertIsNotNone(match, "Manifest 必须声明既有仓库接入能力")
        capability = match.group(1)
        self.assertIn("kind: workflow", capability)
        self.assertIn("path: workflows/infrastructure-adoption", capability)
        self.assertIn("entrypoint: workflows/infrastructure-adoption/ENTRYPOINT.md", capability)
        self.assertIn("- consumer.infrastructure-adoption-harness", capability)
        self.assertIn("- consumer.submodule-preflight", capability)
        tool_match = re.search(
            r"(?ms)^  - id: consumer\.infrastructure-adoption-harness\n(.*?)(?=^  - id: |\Z)",
            MANIFEST,
        )
        self.assertIsNotNone(tool_match, "Harness 安装工具必须单独注册")
        self.assertIn("kind: tool", tool_match.group(1))
        self.assertIn("infrastructure/repository-management/tools/infrastructure-adoption-harness/install_harness.py", tool_match.group(1))
        self.assertTrue((ROOT / "infrastructure/repository-management/tools/infrastructure-adoption-harness/install_harness.py").is_file())
        self.assertTrue((ROOT / "workflows/infrastructure-adoption/WORKFLOW.md").is_file())
        self.assertTrue((ROOT / "workflows/infrastructure-adoption/ADOPT_EXISTING_REPOSITORY.md").is_file())

    def test_prompt_pins_workflow_instructions_to_resolved_commit(self):
        self.assertIn("git ls-remote", PROMPT)
        self.assertIn("<已核对的完整commit>", PROMPT)
        self.assertIn("同一 SHA 下的工作流入口和说明", PROMPT)
        self.assertIn("manifest.yml", PROMPT)
        self.assertNotIn("raw.githubusercontent.com/suanhaitech/suanhai-team-external-expression-infrastructure/main/", PROMPT)
        self.assertIn("才将本提示词转发给小组负责人", PROMPT)

    def test_consumer_rules_are_preserved_and_install_is_idempotent(self):
        for text in (ENTRYPOINT, WORKFLOW, PROMPT):
            self.assertIn("AGENTS.md", text)
            self.assertIn("保留", text)
        self.assertIn("BEGIN suanhai-infrastructure-consumer-harness:v1", INSTALLER)
        self.assertIn("BEGIN suanhai-infrastructure-consumer-harness:v2", INSTALLER)
        self.assertIn("完整 v1 标记段与旧版生成内容完全一致", WORKFLOW)
        self.assertIn("手工修改、标记重复、版本混用", ENTRYPOINT)
        self.assertIn("手工修改过的旧段、版本混用", PROMPT)
        for text in (ENTRYPOINT, WORKFLOW, PROMPT):
            self.assertIn("consumer.infrastructure-adoption-harness", text)
            self.assertIn("--dry-run", text)
            self.assertIn("--apply", text)
            self.assertIn("--expect-plan-sha256", text)

    def test_gitlink_is_locked_and_not_automatically_upgraded(self):
        for text in (ENTRYPOINT, WORKFLOW, PROMPT):
            self.assertIn("git submodule update --remote", text)
            self.assertIn("consumer.submodule-update", text)
        self.assertIn("40 位 SHA", ENTRYPOINT)
        self.assertIn("完整 40 位 commit SHA", WORKFLOW)

    def test_uncommitted_gitlink_does_not_claim_full_preflight_pass(self):
        self.assertIn("提交前", ENTRYPOINT)
        self.assertIn("完整", ENTRYPOINT)
        self.assertIn("父仓 index", ENTRYPOINT)
        self.assertIn("不能为通过检查而擅自提交", WORKFLOW)
        self.assertIn("完整 preflight 会因 HEAD 没有 gitlink", PROMPT)

    def test_consumer_harness_routes_and_preflights_long_term_use(self):
        self.assertIn("consumer.submodule-preflight", ENTRYPOINT)
        self.assertIn("固定版本 Manifest 确实注册 `consumer.submodule-preflight`", ENTRYPOINT)
        self.assertIn("改用只读 Git 查询", ENTRYPOINT)
        self.assertIn("docs/consumer-repository-bootstrap.md", ENTRYPOINT)
        self.assertIn("docs/consumer-repository-harness-v0.1.md", ENTRYPOINT)
        self.assertIn("后续不再需要首次接入提示词", ENTRYPOINT)
        self.assertIn("客户端会自动读取根 `AGENTS.md`", ENTRYPOINT)
        self.assertIn("每次新会话从本仓根目录开始", INSTALLER)

    def test_identity_question_routes_to_repository_role_without_creating_a_task(self):
        for text in (TEMPLATE_HARNESS, INSTALLER, BOOTSTRAP, HARNESS_PROTOCOL):
            self.assertIn("你是谁", text)
            self.assertIn("工作角色", text)
            self.assertIn("不创建任务", text)
        self.assertIn("## 8. 验证身份与仓库定位回答", (ROOT / "docs/consumer-repository-smoke-test.md").read_text(encoding="utf-8"))

    def test_submodule_update_reviews_and_syncs_managed_consumer_harness(self):
        capability = re.search(
            r"(?ms)^  - id: consumer\.submodule-update\n(.*?)(?=^  - id: |\Z)",
            MANIFEST,
        )
        self.assertIsNotNone(capability)
        self.assertIn("- consumer.infrastructure-adoption-harness", capability.group(1))
        for text in (SUBMODULE_UPDATE_ENTRYPOINT, SUBMODULE_UPDATE_WORKFLOW):
            self.assertIn("planned_diff", text)
            self.assertIn("--expect-plan-sha256", text)
            self.assertIn("冲突", text)
            self.assertIn("标记", text)
        self.assertIn("Harness 同步状态", capability.group(1))

    def test_first_prompt_installs_persistent_consumer_harness(self):
        self.assertIn("一次性接入提示词", PROMPT)
        self.assertIn("安装消费端总 Harness", PROMPT)
        self.assertIn("日常任务由本仓根 `AGENTS.md`", PROMPT)
        self.assertIn("本地范围", PROMPT)
        self.assertIn("planned_harness", PROMPT)
        self.assertIn("planned_diff", PROMPT)
        self.assertIn("plan_sha256", PROMPT)
        self.assertIn("Manifest 显式注册", ENTRYPOINT)
        self.assertIn("不得从远端复制工具或手工复制规则", ENTRYPOINT)
        self.assertIn("--expect-plan-sha256", PROMPT)
        self.assertIn("不用等待第二次确认", PROMPT)
        self.assertIn("不重复新增，但继续核对", PROMPT)
        self.assertIn("继续第 5 步确保根 Harness 已安装", PROMPT)
        self.assertIn("仓库原本已有的固定版本缺少此工具", PROMPT)
        self.assertIn("git submodule update --init --recursive -- <实际路径>", PROMPT)
        self.assertIn("工作流来源 SHA 同时用作新 submodule 的固定 SHA", PROMPT)
        self.assertIn("保留原 SHA", PROMPT)

    def test_each_top_level_shared_call_preflights_and_reuses_one_sha_per_workflow(self):
        for text in (TEMPLATE_HARNESS, BOOTSTRAP, HARNESS_PROTOCOL, VERSIONING):
            self.assertIn("独立", text)
            self.assertIn("预检", text)
            self.assertIn("固定 SHA", text)
        self.assertIn("每次准备调用一个独立的顶层共享能力时", TEMPLATE_HARNESS)
        self.assertIn("一次顶层工作流内通过 `uses` 调用的依赖能力沿用", HARNESS_PROTOCOL)
        self.assertIn("暂停该顶层能力，请用户选择", TEMPLATE_HARNESS)
        self.assertIn("不证明候选是快进、包含新能力或已验收", VERSIONING)
        self.assertIn("复用该预检快照", SUBMODULE_UPDATE)
        self.assertIn("作为一次独立的顶层能力调用", ONBOARDING)
        self.assertIn("更新流程复用该预检快照", WORKFLOW)
        self.assertIn("只有用户已授权提交", VERSIONING)
        self.assertIn("若用户未授权提交", SUBMODULE_UPDATE)
        self.assertIn("若提交未获授权", SUBMODULE_UPDATE_WORKFLOW)
        self.assertIn("作为独立顶层共享能力调用时", TASK_LOOP)
        self.assertIn("不在节点间重复查询", HTML_PRODUCTION)


if __name__ == "__main__":
    unittest.main()
