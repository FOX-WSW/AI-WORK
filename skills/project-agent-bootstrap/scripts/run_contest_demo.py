#!/usr/bin/env python3
"""Run the reproducible project-bot-factory contest demo and emit an evidence pack."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
ONBOARD_SCRIPT = SKILL_ROOT / "scripts" / "onboard_project_bot.py"
VALIDATE_SCRIPT = SKILL_ROOT / "scripts" / "validate_scaffold.py"
SENSITIVE_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@", re.IGNORECASE),
    re.compile(
        r"(?<![0-9])(?:10(?:\.[0-9]{1,3}){3}|192\.168(?:\.[0-9]{1,3}){2}|"
        r"172\.(?:1[6-9]|2[0-9]|3[01])(?:\.[0-9]{1,3}){2})(?![0-9])"
    ),
)
SKIP_FIXTURE_PARTS = {".git", "__pycache__", ".venv", "node_modules", "secrets"}


def load_onboard_module():
    spec = importlib.util.spec_from_file_location("contest_onboard_project_bot", ONBOARD_SCRIPT)
    if not spec or not spec.loader:
        raise ValueError(f"cannot load onboarding script: {ONBOARD_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_empty_directory(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"output exists and is not a directory: {path}")
        if any(path.iterdir()):
            raise ValueError(f"refusing to overwrite non-empty output directory: {path}")
    else:
        path.mkdir(parents=True)


def require_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"missing required field: {field}")
    return text


def ensure_case_path(case_root: Path, relative: str, field: str) -> Path:
    path = (case_root / require_text(relative, field)).resolve()
    if case_root.resolve() not in path.parents:
        raise ValueError(f"{field} must stay inside the case directory")
    if not path.exists() or path.is_symlink():
        raise ValueError(f"{field} must exist and must not be a symlink: {path}")
    return path


def scan_fixture(root: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if set(path.relative_to(root).parts) & SKIP_FIXTURE_PARTS:
            continue
        if path.is_symlink():
            raise ValueError(f"contest fixture must not contain symlinks: {path}")
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(pattern.search(text) for pattern in SENSITIVE_PATTERNS):
            raise ValueError(f"contest fixture contains a sensitive-looking value: {path}")
        files.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    if not files:
        raise ValueError("contest fixture contains no files")
    return files


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def run_command(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    return {
        "command": [Path(command[0]).name, *command[1:]],
        "returncode": completed.returncode,
        "output": output,
    }


def count_files(path: Path) -> int:
    return sum(1 for item in path.rglob("*") if item.is_file())


def parse_test_count(output: str) -> int:
    match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    return int(match.group(1)) if match else 0


def render_judge_summary(evidence: dict[str, Any]) -> str:
    metrics = evidence["metrics"]
    stages = evidence["readiness"]
    return f"""# 项目机器人搭建工厂｜比赛闭环证据摘要

## 一句话结果

从“一句业务诉求 + 一组脱敏项目资料”开始，Skill 已自动完成资源评估、资料盘点、知识库地图、机器人安全脚手架、静态校验和生成项目测试。

## 本轮可复核结果

| 结果 | 数值/状态 |
| --- | --- |
| 资料来源登记 | {metrics['source_count']} 项 |
| 本地代码索引 | {metrics['indexed_code_files']} 个文件 |
| 生成知识文件 | {metrics['knowledge_file_count']} 个 |
| 生成机器人项目文件 | {metrics['bot_file_count']} 个 |
| 生成项目测试 | {metrics['generated_test_count']} 项 |
| 脚手架校验 | {'通过' if evidence['checks']['scaffold_validation'] else '未通过'} |
| 生成项目测试 | {'通过' if evidence['checks']['generated_tests'] else '未通过'} |
| 资料盘点就绪 | {'是' if stages['ready_to_inventory'] else '否'} |
| 脚手架生成就绪 | {'是' if stages['ready_to_scaffold'] else '否'} |

## 必须如实说明的边界

- 本轮是可重复的离线黄金案例，不是现场自由问答结果。
- 当前产物是安全脚手架，`scaffold_only=true`、`deployment_ready=false`。
- 未执行飞书真实收发、Codex 在线运行、数据库连接、部署、发布或其他外部写入。
- 真实上线仍需测试群、适配器、密钥注入、监控、恢复和回滚验收。

## 评委看到的产品价值

普通项目同事不需要编写技术方案或配置 JSON；Skill 将不完整资料转为可追溯知识和默认只读的机器人起步项目，并用机器可读证据说明“已完成什么、还缺什么”。
"""


def run_contest_demo(case_root: Path, output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    case_root = case_root.expanduser().resolve()
    output = output.expanduser().resolve()
    case = read_json(case_root / "case.json")
    if case.get("schema_version") != 1:
        raise ValueError("case schema_version must be 1")
    fixture_files = scan_fixture(case_root)
    intake_overlay_path = ensure_case_path(
        case_root, case.get("intake_overlay", ""), "intake_overlay"
    )
    materials_path = ensure_case_path(case_root, case.get("materials", ""), "materials")
    repository_path = ensure_case_path(case_root, case.get("repository", ""), "repository")
    if not materials_path.is_dir() or not repository_path.is_dir():
        raise ValueError("materials and repository must be directories")
    prepare_empty_directory(output)

    workspace = output / "workspace"
    evidence_root = output / "evidence"
    evidence_root.mkdir()
    onboard = load_onboard_module()
    project_name = require_text(case.get("project_name"), "project_name")
    onboard.initialize_workspace(
        workspace,
        name=project_name,
        slug=onboard.derive_slug(project_name, str(case.get("slug") or "")),
        channel=str(case.get("channel") or "feishu"),
        deployment=str(case.get("deployment") or "systemd"),
        secret_mode=str(case.get("secret_mode") or "env"),
        raw_mode=str(case.get("raw_mode") or "copy"),
        desired_capabilities=list(case.get("capabilities") or ["document_qa"]),
    )
    shutil.copytree(materials_path, workspace / "input")
    shutil.copytree(repository_path, workspace / "sample-repo")

    intake_path = workspace / "intake" / "customer-intake.json"
    intake = read_json(intake_path)
    overlay = read_json(intake_overlay_path)
    deep_merge(intake, overlay)
    write_json(intake_path, intake)

    assessment = onboard.assess_workspace(workspace)
    if not assessment["stages"]["ready_to_inventory"]:
        raise ValueError("contest fixture did not reach ready_to_inventory")
    if not assessment["stages"]["ready_to_scaffold"]:
        raise ValueError("contest fixture did not reach ready_to_scaffold")
    inventory = onboard.inventory_workspace(workspace)
    build = onboard.build_bot_from_workspace(workspace)
    bot_root = Path(build["bot_output"])

    validator = run_command([sys.executable, str(VALIDATE_SCRIPT), str(bot_root)], cwd=SKILL_ROOT)
    (evidence_root / "scaffold-validation.log").write_text(
        validator["output"] + "\n", encoding="utf-8"
    )
    test_env = dict(os.environ)
    test_env["PYTHONPATH"] = str(bot_root / "src")
    generated_tests = run_command(
        [sys.executable, "-m", "unittest", "discover", "-s", str(bot_root / "tests"), "-v"],
        cwd=bot_root,
        env=test_env,
    )
    (evidence_root / "generated-tests.log").write_text(
        generated_tests["output"] + "\n", encoding="utf-8"
    )

    bot_manifest = read_json(bot_root / ".project-agent-bootstrap.json")
    source_manifest = read_json(workspace / "knowledge" / "raw" / "source-manifest.json")
    repository_manifest = read_json(
        workspace / "knowledge" / "raw" / "repository-manifest.json"
    )
    indexed_code_files = sum(
        int(item.get("file_count") or 0) for item in repository_manifest.get("repositories", [])
    )
    generated_test_count = parse_test_count(generated_tests["output"])
    checks = {
        "fixture_sanitized": True,
        "ready_to_inventory": assessment["stages"]["ready_to_inventory"],
        "ready_to_scaffold": assessment["stages"]["ready_to_scaffold"],
        "source_inventory_created": bool(source_manifest.get("sources")),
        "code_index_created": indexed_code_files > 0,
        "scaffold_validation": validator["returncode"] == 0,
        "generated_tests": generated_tests["returncode"] == 0 and generated_test_count > 0,
        "scaffold_only_preserved": bot_manifest.get("scaffold_only") is True,
        "deployment_not_overclaimed": bot_manifest.get("deployment_ready") is False,
        "no_external_write": True,
    }
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    evidence = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "case": {
            "case_id": require_text(case.get("case_id"), "case_id"),
            "title": require_text(case.get("title"), "title"),
            "user_request": require_text(case.get("user_request"), "user_request"),
            "mode": "offline_reproducible_fixture",
            "fixture_files": fixture_files,
        },
        "run": {
            "duration_ms": duration_ms,
            "external_write_performed": False,
            "live_feishu_test_performed": False,
            "live_codex_test_performed": False,
        },
        "readiness": assessment["stages"],
        "enabled_capabilities": assessment["enabled_capabilities"],
        "disabled_capabilities": assessment["disabled_capabilities"],
        "metrics": {
            "source_count": len(source_manifest.get("sources", [])),
            "indexed_code_files": indexed_code_files,
            "knowledge_file_count": count_files(workspace / "knowledge"),
            "bot_file_count": count_files(bot_root),
            "generated_test_count": generated_test_count,
            "duration_ms": duration_ms,
        },
        "checks": checks,
        "passed": all(checks.values()),
        "artifacts": {
            "workspace": "workspace",
            "progress_report": "workspace/outputs/搭建进度.md",
            "knowledge_quality_report": "workspace/knowledge/evidence/quality-report.md",
            "customer_handoff": "workspace/bot/CUSTOMER_HANDOFF.md",
            "bot_manifest": "workspace/bot/.project-agent-bootstrap.json",
        },
        "limitations": [
            "黄金案例使用预置脱敏资料和结构化 intake overlay，不代表现场自由对话质量。",
            "生成项目仍缺少真实飞书和 Codex 适配器及常驻 serve 入口。",
            "未执行真实外部系统写入、部署或生产连接。",
        ],
    }
    write_json(evidence_root / "contest-evidence.json", evidence)
    (evidence_root / "评委摘要.md").write_text(render_judge_summary(evidence), encoding="utf-8")
    manifest_files = sorted(path for path in output.rglob("*") if path.is_file())
    write_json(
        evidence_root / "manifest.json",
        {
            "schema_version": 1,
            "generated_at": evidence["generated_at"],
            "files": [
                {
                    "path": str(path.relative_to(output)),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
                for path in manifest_files
                if path != evidence_root / "manifest.json"
            ],
        },
    )
    return {
        "status": "completed",
        "passed": evidence["passed"],
        "output": str(output),
        "case_id": evidence["case"]["case_id"],
        "metrics": evidence["metrics"],
        "readiness": evidence["readiness"],
        "scaffold_only": bot_manifest.get("scaffold_only"),
        "deployment_ready": bot_manifest.get("deployment_ready"),
        "external_write_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, help="Contest fixture directory containing case.json")
    parser.add_argument("--output", required=True, help="New or empty directory for the demo and evidence")
    args = parser.parse_args()
    try:
        result = run_contest_demo(Path(args.case), Path(args.output))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
