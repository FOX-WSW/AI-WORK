from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "onboard_project_bot.py"
SPEC = importlib.util.spec_from_file_location("onboard_project_bot", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OnboardingTests(unittest.TestCase):
    def initialize(
        self,
        root: Path,
        *,
        secret_mode: str = "env",
        raw_mode: str = "reference",
        desired_capabilities: list[str] | None = None,
    ) -> Path:
        workspace = root / "customer-workspace"
        MODULE.initialize_workspace(
            workspace,
            name="示例客户项目",
            slug="example-customer",
            channel="feishu",
            deployment="systemd",
            secret_mode=secret_mode,
            raw_mode=raw_mode,
            desired_capabilities=desired_capabilities,
        )
        return workspace

    def test_init_creates_guided_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.initialize(Path(directory))
            self.assertTrue((workspace / "intake/customer-intake.json").is_file())
            self.assertTrue((workspace / "intake/资源收集表.md").is_file())
            self.assertTrue((workspace / "intake/资源填写示例.json").is_file())
            self.assertTrue((workspace / "secrets/local-secrets.example.txt").is_file())
            self.assertTrue((workspace / "outputs/搭建进度.md").is_file())
            for name in ("raw", "wiki", "maps", "evidence", "sync"):
                self.assertTrue((workspace / "knowledge" / name).is_dir())
            gitignore = (workspace / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("secrets/*.txt", gitignore)
            intake = json.loads((workspace / "intake/customer-intake.json").read_text(encoding="utf-8"))
            self.assertEqual(intake["desired_capabilities"], ["document_qa"])
            self.assertIn("不需要编辑 JSON", (workspace / "intake/资源收集表.md").read_text(encoding="utf-8"))

    def test_incomplete_intake_returns_staged_gap_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.initialize(Path(directory))
            report = MODULE.assess_workspace(workspace)
            self.assertFalse(report["stages"]["ready_to_scaffold"])
            self.assertFalse(report["stages"]["ready_for_live_readonly"])
            self.assertFalse(report["secret_values_exposed"])
            self.assertTrue((workspace / "outputs/intake-report.md").is_file())
            self.assertTrue((workspace / "outputs/搭建进度.md").is_file())
            self.assertLessEqual(len(report["next_actions"]), 5)

    def test_chinese_name_gets_deterministic_slug(self) -> None:
        first = MODULE.derive_slug("新零售项目")
        second = MODULE.derive_slug("新零售项目")
        self.assertEqual(first, second)
        self.assertRegex(first, r"^project-[0-9a-f]{8}$")

    def test_documents_only_customer_can_reach_inventory_and_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "manual.md"
            source.write_text("业务操作手册", encoding="utf-8")
            workspace = self.initialize(root)
            intake_path = workspace / "intake/customer-intake.json"
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            intake["project"].update({"business_scope": "文档问答", "owners": ["管理员"]})
            intake["deployment"].update(
                {"os": "Linux", "architecture": "x86_64", "working_directory": "/opt/doc-bot"}
            )
            intake["desired_capabilities"] = ["document_qa"]
            intake["knowledge"]["local_documents"] = [str(source)]
            intake_path.write_text(
                json.dumps(intake, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            report = MODULE.assess_workspace(workspace)
            self.assertTrue(report["stages"]["ready_to_inventory"])
            self.assertTrue(report["stages"]["ready_to_scaffold"])
            self.assertEqual(report["enabled_capabilities"], ["document_qa"])

    def test_unsupported_channel_does_not_claim_scaffold_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.initialize(Path(directory))
            intake_path = workspace / "intake/customer-intake.json"
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            intake["project"].update({"business_scope": "消息问答", "owners": ["管理员"]})
            intake["deployment"].update(
                {"os": "Linux", "architecture": "x86_64", "working_directory": "/opt/msg-bot"}
            )
            intake["channel"]["type"] = "wecom"
            intake_path.write_text(
                json.dumps(intake, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            report = MODULE.assess_workspace(workspace)
            self.assertFalse(report["stages"]["ready_to_scaffold"])
            self.assertTrue(any(item["field"] == "channel.type" for item in report["missing"]))

    def test_inventory_copies_documents_and_skips_secret_like_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "功能设计.md").write_text("订单创建流程", encoding="utf-8")
            (source / "password.txt").write_text("do-not-copy", encoding="utf-8")
            workspace = self.initialize(root, raw_mode="copy")
            intake_path = workspace / "intake/customer-intake.json"
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            intake["knowledge"]["local_documents"] = [
                {"label": "项目资料", "path": str(source)}
            ]
            intake_path.write_text(
                json.dumps(intake, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            result = MODULE.inventory_workspace(workspace)
            self.assertEqual(result["source_count"], 1)
            self.assertTrue((workspace / "knowledge/evidence/build-plan.md").is_file())
            manifest = json.loads(
                (workspace / "knowledge/raw/source-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["sources"][0]["relative_path"], "功能设计.md")
            self.assertNotIn("password.txt", json.dumps(manifest, ensure_ascii=False))
            overview = (workspace / "knowledge/wiki/项目总览.md").read_text(encoding="utf-8")
            self.assertIn("src-00001", overview)
            self.assertIn("项目资料", overview)

    def test_relative_document_path_is_resolved_from_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.initialize(Path(directory), raw_mode="copy")
            source = workspace / "待导入资料"
            source.mkdir()
            (source / "操作手册.md").write_text("收货流程", encoding="utf-8")
            intake_path = workspace / "intake/customer-intake.json"
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            intake["knowledge"]["local_documents"] = [{"label": "手册", "path": "./待导入资料"}]
            intake_path.write_text(json.dumps(intake, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report = MODULE.assess_workspace(workspace)
            self.assertTrue(report["stages"]["ready_to_inventory"])
            result = MODULE.inventory_workspace(workspace)
            self.assertEqual(result["source_count"], 1)

    def test_local_repository_gets_bounded_code_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.initialize(Path(directory), desired_capabilities=["code_analysis"])
            repository = workspace / "repos/order-service/src/main/java"
            repository.mkdir(parents=True)
            (repository / "OrderController.java").write_text("class OrderController {}", encoding="utf-8")
            (repository / "OrderService.java").write_text("class OrderService {}", encoding="utf-8")
            (repository / "api_token.txt").write_text("must-not-index", encoding="utf-8")
            intake_path = workspace / "intake/customer-intake.json"
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            intake["repositories"] = [
                {"name": "order-service", "local_path": "./repos/order-service", "allowed_branches": ["main"], "secret_refs": []}
            ]
            intake_path.write_text(json.dumps(intake, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report = MODULE.assess_workspace(workspace)
            self.assertTrue(report["stages"]["ready_to_inventory"])
            MODULE.inventory_workspace(workspace)
            repository_manifest = json.loads(
                (workspace / "knowledge/raw/repository-manifest.json").read_text(encoding="utf-8")
            )
            indexed = repository_manifest["repositories"][0]
            self.assertEqual(indexed["file_count"], 2)
            self.assertIn("src/main/java/OrderController.java", indexed["entry_hints"])
            self.assertNotIn("api_token.txt", json.dumps(indexed))
            code_map = (workspace / "knowledge/maps/代码检索图.yaml").read_text(encoding="utf-8")
            self.assertIn("indexed_local_readonly", code_map)

    @unittest.skipIf(os.name != "posix", "symlink behavior")
    def test_symlinked_source_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_source = root / "real-source"
            real_source.mkdir()
            (real_source / "doc.md").write_text("data", encoding="utf-8")
            workspace = self.initialize(root)
            link = workspace / "linked-source"
            link.symlink_to(real_source, target_is_directory=True)
            intake_path = workspace / "intake/customer-intake.json"
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            intake["knowledge"]["local_documents"] = ["./linked-source"]
            intake_path.write_text(json.dumps(intake, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report = MODULE.assess_workspace(workspace)
            self.assertFalse(report["stages"]["ready_to_inventory"])
            result = MODULE.inventory_workspace(workspace)
            self.assertEqual(result["source_count"], 0)

    @unittest.skipIf(os.name != "posix", "POSIX permission check")
    def test_file_secret_mode_reports_names_without_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.initialize(Path(directory), secret_mode="file")
            secret_file = workspace / "secrets/local-secrets.txt"
            secret_file.write_text(
                "FEISHU_APP_ID=id-value\nFEISHU_APP_SECRET=secret-value\n",
                encoding="utf-8",
            )
            secret_file.chmod(0o600)
            report = MODULE.assess_workspace(workspace)
            serialized = json.dumps(report, ensure_ascii=False)
            self.assertNotIn("secret-value", serialized)
            self.assertNotIn("id-value", serialized)
            self.assertIn("FEISHU_APP_SECRET", serialized)

    def test_missing_channel_secrets_block_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.initialize(Path(directory), secret_mode="file")
            intake_path = workspace / "intake/customer-intake.json"
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            intake["project"].update({"business_scope": "文档问答", "owners": ["管理员"]})
            intake["channel"].update({"app_ready": True, "event_subscription_ready": True})
            intake["deployment"].update(
                {
                    "os": "Linux",
                    "architecture": "x86_64",
                    "working_directory": "/opt/doc-bot",
                    "host_access_ready": True,
                    "network_ready": True,
                }
            )
            intake_path.write_text(json.dumps(intake, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report = MODULE.assess_workspace(workspace)
            self.assertFalse(report["stages"]["ready_for_dry_run"])
            self.assertTrue(
                any(item["stage"] == "dry_run" and item["field"] == "secret:FEISHU_APP_SECRET" for item in report["missing"])
            )

    @unittest.skipIf(os.name != "posix", "POSIX permission check")
    def test_malformed_secret_file_reports_structure_without_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.initialize(Path(directory), secret_mode="file")
            secret_file = workspace / "secrets/local-secrets.txt"
            secret_file.write_text("FEISHU_APP_ID\n", encoding="utf-8")
            secret_file.chmod(0o600)
            report = MODULE.assess_workspace(workspace)
            serialized = json.dumps(report, ensure_ascii=False)
            self.assertIn("KEY=VALUE", serialized)
            self.assertNotIn("FEISHU_APP_ID\n", serialized)

    @unittest.skipIf(os.name != "posix", "POSIX permission check")
    def test_live_readiness_requires_recorded_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.initialize(root, secret_mode="file")
            source = workspace / "manual.md"
            source.write_text("项目手册", encoding="utf-8")
            intake_path = workspace / "intake/customer-intake.json"
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            intake["project"].update({"business_scope": "文档问答", "owners": ["管理员"]})
            intake["knowledge"]["local_documents"] = ["./manual.md"]
            intake["channel"].update(
                {
                    "app_ready": True,
                    "event_subscription_ready": True,
                    "allowed_chat_ids": ["test-chat"],
                }
            )
            intake["deployment"].update(
                {
                    "os": "Linux",
                    "architecture": "x86_64",
                    "working_directory": "/opt/doc-bot",
                    "host_access_ready": True,
                    "network_ready": True,
                    "maintenance_owner": "IT",
                }
            )
            intake_path.write_text(json.dumps(intake, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            secret_file = workspace / "secrets/local-secrets.txt"
            secret_file.write_text("FEISHU_APP_ID=id\nFEISHU_APP_SECRET=secret\n", encoding="utf-8")
            secret_file.chmod(0o600)
            before = MODULE.assess_workspace(workspace)
            self.assertTrue(before["stages"]["ready_for_dry_run"])
            self.assertFalse(before["stages"]["ready_for_live_readonly"])
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            for check in ("bot_identity", "event_subscription", "test_message", "codex_runtime"):
                intake["verification"][check] = {"status": "verified", "evidence": f"{check}-ok"}
            intake_path.write_text(json.dumps(intake, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            after = MODULE.assess_workspace(workspace)
            self.assertTrue(after["stages"]["ready_for_live_readonly"])

    def test_ready_workspace_builds_one_bot_with_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.initialize(root)
            source = workspace / "manual.md"
            source.write_text("订单操作手册", encoding="utf-8")
            intake_path = workspace / "intake/customer-intake.json"
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            intake["project"].update({"business_scope": "订单资料问答", "owners": ["项目经理"]})
            intake["knowledge"]["local_documents"] = ["./manual.md"]
            intake["deployment"].update(
                {"os": "Linux", "architecture": "x86_64", "working_directory": "/opt/order-bot"}
            )
            intake_path.write_text(json.dumps(intake, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            MODULE.inventory_workspace(workspace)
            result = MODULE.build_bot_from_workspace(workspace)
            bot = Path(result["bot_output"])
            self.assertTrue((bot / "CUSTOMER_HANDOFF.md").is_file())
            self.assertTrue((bot / "knowledge/wiki/项目总览.md").is_file())
            self.assertFalse(result["ready_for_live_readonly"])


if __name__ == "__main__":
    unittest.main()
