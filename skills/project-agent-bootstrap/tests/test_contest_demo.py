from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "run_contest_demo.py"
CASE = SKILL_ROOT / "assets" / "contest-demo-case"
SPEC = importlib.util.spec_from_file_location("run_contest_demo", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ContestDemoTests(unittest.TestCase):
    def test_golden_case_builds_scaffold_and_evidence_pack(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "contest-output"
            result = MODULE.run_contest_demo(CASE, output)
            self.assertTrue(result["passed"])
            self.assertTrue(result["scaffold_only"])
            self.assertFalse(result["deployment_ready"])
            self.assertFalse(result["external_write_performed"])
            self.assertGreaterEqual(result["metrics"]["source_count"], 3)
            self.assertEqual(result["metrics"]["indexed_code_files"], 2)
            self.assertGreater(result["metrics"]["generated_test_count"], 0)

            evidence_path = output / "evidence" / "contest-evidence.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["case"]["mode"], "offline_reproducible_fixture")
            self.assertTrue(all(evidence["checks"].values()))
            self.assertFalse(evidence["run"]["live_feishu_test_performed"])
            self.assertFalse(evidence["run"]["live_codex_test_performed"])
            self.assertTrue((output / "evidence" / "评委摘要.md").is_file())
            self.assertTrue((output / "evidence" / "manifest.json").is_file())
            self.assertTrue((output / "workspace" / "bot" / "CUSTOMER_HANDOFF.md").is_file())

    def test_refuses_to_overwrite_non_empty_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "contest-output"
            output.mkdir()
            (output / "keep.txt").write_text("user data", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                MODULE.run_contest_demo(CASE, output)
            self.assertEqual((output / "keep.txt").read_text(encoding="utf-8"), "user data")

    def test_live_readiness_is_not_required_or_overclaimed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "contest-output"
            result = MODULE.run_contest_demo(CASE, output)
            self.assertFalse(result["readiness"]["ready_for_dry_run"])
            self.assertFalse(result["readiness"]["ready_for_live_readonly"])
            summary = (output / "evidence" / "评委摘要.md").read_text(encoding="utf-8")
            self.assertIn("deployment_ready=false", summary)
            self.assertIn("未执行飞书真实收发", summary)


if __name__ == "__main__":
    unittest.main()
