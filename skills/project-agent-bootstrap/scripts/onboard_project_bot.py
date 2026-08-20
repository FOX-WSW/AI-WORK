#!/usr/bin/env python3
"""Initialize and assess a customer project-bot onboarding workspace."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DOCUMENT_SUFFIXES = {
    ".csv",
    ".doc",
    ".docx",
    ".html",
    ".htm",
    ".json",
    ".md",
    ".pdf",
    ".ppt",
    ".pptx",
    ".sql",
    ".txt",
    ".xls",
    ".xlsx",
    ".yaml",
    ".yml",
}
CODE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".gradle",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".php",
    ".properties",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".ts",
    ".tsx",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}
SKIP_PARTS = {
    ".git",
    ".idea",
    ".venv",
    "__pycache__",
    "node_modules",
    "secrets",
}
GENERATED_WORKSPACE_PARTS = {"artifacts", "bot", "data", "intake", "knowledge", "logs", "outputs"}
CODE_SKIP_PARTS = SKIP_PARTS | GENERATED_WORKSPACE_PARTS | {"build", "coverage", "dist", "target", "vendor"}
SENSITIVE_NAME_FRAGMENTS = {
    "credential",
    "cookie",
    "password",
    "private_key",
    "secret",
    "token",
}
CAPABILITY_REQUIREMENTS = {
    "document_qa": "至少一项本地资料、功能设计或云文档",
    "code_analysis": "至少一个代码仓库或本地代码目录",
    "database_diagnostics": "至少一个专用只读数据库环境",
    "log_analysis": "至少一个只读日志源",
}
SUPPORTED_CAPABILITIES = tuple(CAPABILITY_REQUIREMENTS)
CAPABILITY_LABELS = {
    "document_qa": "项目资料问答",
    "code_analysis": "代码检索与分析",
    "database_diagnostics": "数据库只读诊断",
    "log_analysis": "日志只读排查",
}
SECRET_KEY_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{1,127}")
STAGE_ORDER = {"inventory": 0, "scaffold": 1, "dry_run": 2, "live_readonly": 3}
WIKI_FILES = {
    "项目总览.md": "项目范围、用户、系统、阶段和权威资料顺序。",
    "业务与系统架构.md": "业务域、系统边界、上下游关系和集成方式。",
    "核心业务流程.md": "用业务语言描述关键流程、状态和异常分支。",
    "环境与系统边界.md": "环境、网络、访问边界和允许的只读能力。",
    "核心业务链路与数据模型.md": "业务对象、主键、表关系和样本验证结论。",
    "功能与代码索引.md": "功能、页面、接口、服务、代码、表和日志关键词的对应关系。",
    "常见问题与处理经验.md": "经过审核的故障现象、证据、原因、处理和验证方式。",
    "资料地图.md": "资料来源、权威性、更新时间、责任人和适用范围。",
}
MAP_FILES = {
    "资料地图.yaml": "source-map",
    "环境地图.yaml": "environment-map",
    "数据表结构地图.yaml": "data-map",
    "业务核心链路图.yaml": "business-flow-map",
    "功能入口图.yaml": "function-entry-map",
    "代码检索图.yaml": "code-search-map",
    "日志检索图.yaml": "log-search-map",
    "术语字典.yaml": "glossary",
    "权限角色地图.yaml": "role-policy-map",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,62}", slug):
        raise ValueError("slug must start with a letter and contain 2-63 lowercase ASCII characters")
    return slug


def derive_slug(name: str, explicit: str = "") -> str:
    if explicit.strip():
        return slugify(explicit)
    ascii_candidate = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if ascii_candidate and ascii_candidate[0].isalpha():
        candidate = ascii_candidate[:63].rstrip("-")
        if len(candidate) >= 2:
            return slugify(candidate)
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    return f"project-{digest}"


def parse_capabilities(raw: str) -> list[str]:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if not values:
        values = ["document_qa"]
    invalid = sorted(set(values) - set(SUPPORTED_CAPABILITIES))
    if invalid:
        raise ValueError("unsupported capabilities: " + ", ".join(invalid))
    return list(dict.fromkeys(values))


def resolve_workspace_path(workspace: Path, raw_path: str) -> tuple[Path, Path]:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = workspace / candidate
    return candidate, candidate.resolve()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def prepare_empty_directory(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"output exists and is not a directory: {path}")
        if any(path.iterdir()):
            raise ValueError(f"refusing to overwrite non-empty directory: {path}")
    else:
        path.mkdir(parents=True)


def initial_intake(
    *,
    name: str,
    slug: str,
    channel: str,
    deployment: str,
    secret_mode: str,
    raw_mode: str,
    desired_capabilities: list[str],
) -> dict[str, Any]:
    service_manager = {
        "local": "none",
        "launchd": "launchd",
        "systemd": "systemd",
        "docker": "docker",
        "hosted": "systemd",
    }[deployment]
    channel_secret_refs = {
        "feishu": ["FEISHU_APP_ID", "FEISHU_APP_SECRET"],
        "lark": ["LARK_APP_ID", "LARK_APP_SECRET"],
        "dingtalk": ["DINGTALK_APP_KEY", "DINGTALK_APP_SECRET"],
        "wecom": ["WECOM_CORP_ID", "WECOM_APP_SECRET"],
        "web": [],
    }[channel]
    return {
        "schema_version": 1,
        "project": {
            "display_name": name,
            "slug": slug,
            "business_scope": "",
            "out_of_scope": [],
            "owners": [],
            "target_roles": ["business", "it"],
            "answer_language": "zh-CN",
            "timezone": "Asia/Shanghai",
        },
        "desired_capabilities": desired_capabilities,
        "channel": {
            "type": channel,
            "bot_name": f"{name}智能机器人",
            "app_ready": False,
            "event_subscription_ready": False,
            "allowed_chat_ids": [],
            "allow_direct_messages": False,
            "reply_in_topic": True,
            "secret_refs": channel_secret_refs,
        },
        "deployment": {
            "type": deployment,
            "os": "",
            "architecture": "",
            "service_manager": service_manager,
            "host_access_ready": False,
            "network_ready": False,
            "working_directory": "",
            "maintenance_owner": "",
        },
        "secret_provider": {
            "mode": secret_mode,
            "file_path": "secrets/local-secrets.txt" if secret_mode == "file" else "",
        },
        "knowledge": {
            "raw_mode": raw_mode,
            "local_documents": [],
            "functional_designs": [],
            "cloud_documents": [],
            "authoritative_order": [
                "project_rules",
                "wiki",
                "functional_design",
                "code",
                "database",
                "logs",
            ],
        },
        "databases": [],
        "repositories": [],
        "log_sources": [],
        "cloud_services": [],
        "verification": {
            "bot_identity": {"status": "not_checked", "evidence": ""},
            "event_subscription": {"status": "not_checked", "evidence": ""},
            "test_message": {"status": "not_checked", "evidence": ""},
            "codex_runtime": {"status": "not_checked", "evidence": ""},
            "read_only_connectors": {"status": "not_checked", "evidence": ""},
        },
        "safety": {
            "dry_run": True,
            "allow_real_writes": False,
            "read_only_by_default": True,
            "knowledge_write_requires_review": True,
        },
    }


def initialize_knowledge_tree(root: Path, project_name: str) -> None:
    knowledge = root / "knowledge"
    write_json(
        knowledge / "raw" / "source-manifest.json",
        {"schema_version": 1, "generated_at": None, "sources": [], "skipped": []},
    )
    write_json(
        knowledge / "raw" / "repository-manifest.json",
        {"schema_version": 1, "generated_at": None, "repositories": []},
    )
    for filename, purpose in WIKI_FILES.items():
        write_text(
            knowledge / "wiki" / filename,
            f"# {filename.removesuffix('.md')}\n\n"
            f"> 项目：{project_name}  \n"
            "> 状态：待首轮资料梳理  \n"
            "> 规则：所有结论必须能够回溯到 raw、代码、数据库元数据或日志证据。\n\n"
            f"本页用于记录：{purpose}\n",
        )
    for filename, map_type in MAP_FILES.items():
        write_text(
            knowledge / "maps" / filename,
            "version: 1\n"
            f"map_type: {map_type}\n"
            "generated_at: null\n"
            "entries: []\n",
        )
    write_text(
        knowledge / "evidence" / "quality-report.md",
        "# 知识库质量报告\n\n尚未执行首轮资料盘点。\n",
    )
    write_text(knowledge / "evidence" / "knowledge-candidates.jsonl", "")
    write_json(
        knowledge / "sync" / "sync-state.json",
        {"schema_version": 1, "last_inventory_at": None, "sources": {}},
    )


def initialize_workspace(
    output: Path,
    *,
    name: str,
    slug: str,
    channel: str,
    deployment: str,
    secret_mode: str,
    raw_mode: str,
    desired_capabilities: list[str] | None = None,
) -> dict[str, Any]:
    output = output.expanduser().resolve()
    prepare_empty_directory(output)
    intake = initial_intake(
        name=name,
        slug=slug,
        channel=channel,
        deployment=deployment,
        secret_mode=secret_mode,
        raw_mode=raw_mode,
        desired_capabilities=desired_capabilities or ["document_qa"],
    )
    write_json(output / "intake" / "customer-intake.json", intake)
    write_text(
        output / "intake" / "资源收集表.md",
        f"# {name}机器人客户需求表\n\n"
        "不懂的项直接写“不知道”或“需要 IT 协助”。你不需要编辑 JSON，"
        "把答案告诉 Codex，由 Skill 更新技术配置。\n\n"
        "本表禁止填写密码、Token、Cookie 或私钥真值。\n\n"
        "## 第一批：先说清楚想要什么\n\n"
        "1. 机器人主要帮大家解决什么问题？\n\n   > 填写：\n\n"
        "2. 谁会使用？（业务、IT、开发、管理者）\n\n   > 填写：\n\n"
        "3. 想先做哪些能力？（资料问答、代码、数据库、日志）\n\n"
        f"   > 当前默认：{'、'.join(CAPABILITY_LABELS[item] for item in intake['desired_capabilities'])}\n\n"
        "4. 哪些事情明确不允许机器人做？\n\n   > 默认：不写数据、不发布、不重启、不删除\n\n"
        "## 第二批：把现有资料交给它\n\n"
        "- 本地资料文件夹或文件：\n"
        "- 功能设计、操作手册、培训资料：\n"
        "- 飞书云文档链接：\n"
        "- 代码仓库链接或本地目录：\n"
        "- 数据库有哪些环境：\n"
        "- 日志在哪里看：\n\n"
        "- 还需要访问哪些云服务或业务 API：\n\n"
        "## 第三批：上线时再确认\n\n"
        "- 飞书应用/机器人是否已创建：\n"
        "- 先在哪个测试群验收：\n"
        "- 运行在本地 Mac、客户 Linux 服务器还是托管服务器：\n"
        "- 谁负责后续运维：\n\n"
        "进度和下一步以 `outputs/搭建进度.md` 为准。\n",
    )
    write_json(
        output / "intake" / "资源填写示例.json",
        {
            "knowledge": {
                "local_documents": [{"label": "项目资料", "path": "./待导入资料"}],
                "cloud_documents": [
                    {"label": "项目首页", "url": "https://example.com/project-doc"}
                ],
            },
            "repositories": [
                {
                    "name": "example-service",
                    "url": "https://example.com/team/example-service.git",
                    "allowed_branches": ["main"],
                    "secret_refs": ["GIT_READ_TOKEN"],
                }
            ],
            "databases": [
                {
                    "environment": "UAT",
                    "engine": "oracle",
                    "host": "db.example.internal",
                    "port": 1521,
                    "database_or_service": "UATDB",
                    "schema": "APP_READONLY",
                    "read_only": True,
                    "secret_refs": {
                        "dsn": "DB_UAT_DSN",
                        "user": "DB_UAT_USER",
                        "password": "DB_UAT_PASSWORD",
                    },
                }
            ],
            "log_sources": [
                {
                    "name": "UAT 日志",
                    "provider": "rancher",
                    "environment": "UAT",
                    "secret_refs": ["LOG_READ_TOKEN"],
                }
            ],
        },
    )
    initialize_knowledge_tree(output, name)
    write_text(
        output / "secrets" / "local-secrets.example.txt",
        "# Optional local TXT secret file. Copy to local-secrets.txt and set chmod 600.\n"
        "# Use KEY=VALUE. Never commit, upload, or include this file in the knowledge base.\n"
        + "\n".join(f"{key}=<set-locally>" for key in intake["channel"]["secret_refs"])
        + "\n",
    )
    write_text(
        output / ".gitignore",
        ".env\nsecrets/*.txt\nsecrets/*.env\n!secrets/*.example.txt\n"
        "data/\nlogs/\nartifacts/\nknowledge/raw/files/\n",
    )
    write_text(
        output / "START_HERE.md",
        f"# {name}机器人搭建工作区\n\n"
        "1. 打开 `intake/资源收集表.md`，或直接继续和 Codex 对话。不知道的项允许稍后补。\n"
        "2. 由 Codex 将答案写入 `intake/customer-intake.json`；新同事不需要手工编辑它。\n"
        "3. 密码和 Token 选择环境变量，或复制 `secrets/local-secrets.example.txt` 为 "
        "`secrets/local-secrets.txt` 后本机填写。\n"
        "4. Skill 运行 `assess`，生成人能看懂的 `outputs/搭建进度.md`。\n"
        "5. 资料就绪后运行 `inventory`，生成首轮 Wiki、资料地图和待验证项。\n"
        "6. 达到生成门槛后运行 `build-bot`；真实飞书发送与服务安装仍需单独授权和验收。\n",
    )
    initial_report = assess_workspace(output)
    return {
        "status": "initialized",
        "workspace": str(output),
        "intake": str(output / "intake" / "customer-intake.json"),
        "secret_mode": secret_mode,
        "customer_form": str(output / "intake" / "资源收集表.md"),
        "progress": str(output / "outputs" / "搭建进度.md"),
        "ready_to_inventory": initial_report["stages"]["ready_to_inventory"],
        "next": ["answer_first_batch", "assess", "inventory", "build-bot"],
    }


def load_intake(workspace: Path) -> dict[str, Any]:
    path = workspace / "intake" / "customer-intake.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing intake file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid intake JSON: {exc}") from exc
    if value.get("schema_version") != 1:
        raise ValueError("unsupported intake schema_version")
    return value


def present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def collect_secret_requirements(intake: dict[str, Any]) -> dict[str, str]:
    requirements: dict[str, str] = {}

    def register(raw_name: Any, stage: str) -> None:
        name = str(raw_name).strip()
        if not name:
            return
        current = requirements.get(name)
        if current is None or STAGE_ORDER[stage] < STAGE_ORDER[current]:
            requirements[name] = stage

    for ref in intake.get("channel", {}).get("secret_refs", []):
        register(ref, "dry_run")
    for section in ("databases", "repositories", "log_sources", "cloud_services"):
        for item in intake.get(section, []):
            raw = item.get("secret_refs", [])
            if isinstance(raw, dict):
                for value in raw.values():
                    register(value, "live_readonly")
            else:
                for value in raw:
                    register(value, "live_readonly")
    return dict(sorted(requirements.items()))


def inspect_secret_file(path: Path) -> tuple[set[str], str | None]:
    if path.is_symlink():
        return set(), "TXT 密钥文件不能是符号链接"
    if not path.is_file():
        return set(), "TXT 密钥文件不存在或不是普通文件"
    if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) & 0o077:
        return set(), "TXT 密钥文件权限必须是 0600"
    keys: set[str] = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return set(), f"TXT 密钥文件第 {line_number} 行必须使用 KEY=VALUE"
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not SECRET_KEY_PATTERN.fullmatch(key):
            return set(), f"TXT 密钥文件第 {line_number} 行的变量名不合法"
        if key in keys:
            return set(), f"TXT 密钥文件包含重复变量：{key}"
        if not value or value == "<set-locally>":
            continue
        keys.add(key)
    return keys, None


def assess_workspace(workspace: Path) -> dict[str, Any]:
    workspace = workspace.expanduser().resolve()
    intake = load_intake(workspace)
    missing: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def require(stage: str, field: str, value: Any, message: str) -> None:
        if not present(value):
            missing.append({"stage": stage, "field": field, "message": message})

    project = intake.get("project", {})
    require("scaffold", "project.business_scope", project.get("business_scope"), "请说明机器人覆盖的业务范围")
    require("scaffold", "project.owners", project.get("owners"), "请指定项目负责人或机器人管理员")
    require("scaffold", "project.target_roles", project.get("target_roles"), "请选择业务、IT、开发或管理等使用角色")

    channel = intake.get("channel", {})
    if str(channel.get("type") or "").lower() != "feishu":
        missing.append(
            {
                "stage": "scaffold",
                "field": "channel.type",
                "message": "当前可生成的运行时仅支持 feishu；其他渠道可先完成资源盘点，需补充对应适配器",
            }
        )
    require("dry_run", "channel.app_ready", channel.get("app_ready"), "请创建或确认消息平台应用/机器人")
    require(
        "dry_run",
        "channel.event_subscription_ready",
        channel.get("event_subscription_ready"),
        "请确认消息事件订阅或长连接已经配置",
    )
    require("live_readonly", "channel.allowed_chat_ids", channel.get("allowed_chat_ids"), "正式运行前必须配置非空会话白名单")

    deployment = intake.get("deployment", {})
    if str(deployment.get("service_manager") or "none") not in {"none", "launchd", "systemd"}:
        missing.append(
            {
                "stage": "scaffold",
                "field": "deployment.service_manager",
                "message": "当前脚手架支持本地、launchd 和 systemd；Docker 需先补充可验收的镜像与启动模板",
            }
        )
    require("scaffold", "deployment.os", deployment.get("os"), "请填写运行主机操作系统")
    require("scaffold", "deployment.architecture", deployment.get("architecture"), "请填写主机架构，例如 arm64 或 x86_64")
    require("dry_run", "deployment.host_access_ready", deployment.get("host_access_ready"), "请确认部署主机可访问")
    require("dry_run", "deployment.network_ready", deployment.get("network_ready"), "请确认消息平台、代码、数据库和日志网络可达")
    require("scaffold", "deployment.working_directory", deployment.get("working_directory"), "请填写机器人工作目录")
    require("live_readonly", "deployment.maintenance_owner", deployment.get("maintenance_owner"), "请指定运行维护负责人")

    capabilities = set(intake.get("desired_capabilities", []))
    knowledge = intake.get("knowledge", {})
    knowledge_sources = []
    for section in ("local_documents", "functional_designs"):
        for index, item in enumerate(knowledge.get(section, [])):
            raw_path = item if isinstance(item, str) else item.get("path", "")
            raw_path = str(raw_path or "").strip()
            field = f"knowledge.{section}[{index}]"
            if not raw_path:
                missing.append({"stage": "inventory", "field": field, "message": "本地资料需要可读路径"})
                continue
            candidate, resolved = resolve_workspace_path(workspace, raw_path)
            if candidate.is_symlink():
                missing.append({"stage": "inventory", "field": field, "message": "资料根路径不能是符号链接"})
                continue
            if not resolved.exists():
                missing.append({"stage": "inventory", "field": field, "message": f"资料路径不存在：{candidate}"})
                continue
            knowledge_sources.append(item)
    for index, item in enumerate(knowledge.get("cloud_documents", [])):
        url = item if isinstance(item, str) else item.get("url", "")
        if str(url or "").strip():
            knowledge_sources.append(item)
        else:
            missing.append(
                {
                    "stage": "inventory",
                    "field": f"knowledge.cloud_documents[{index}]",
                    "message": "云文档需要链接或可解析的文档标识",
                }
            )
    valid_repositories = []
    for index, repository in enumerate(intake.get("repositories", [])):
        field = f"repositories[{index}]"
        if not str(repository.get("name") or "").strip():
            missing.append({"stage": "inventory", "field": field, "message": "代码仓需要名称"})
            continue
        if not str(repository.get("local_path") or repository.get("url") or "").strip():
            missing.append({"stage": "inventory", "field": field, "message": "代码仓需要本地路径或 Git URL"})
            continue
        local_path = str(repository.get("local_path") or "").strip()
        remote_url = str(repository.get("url") or "").strip()
        if local_path and not remote_url:
            candidate, resolved = resolve_workspace_path(workspace, local_path)
            if candidate.is_symlink():
                missing.append({"stage": "inventory", "field": field, "message": "代码仓根路径不能是符号链接"})
                continue
            if not resolved.is_dir():
                missing.append({"stage": "inventory", "field": field, "message": f"本地代码目录不存在：{candidate}"})
                continue
        if not repository.get("allowed_branches"):
            missing.append({"stage": "inventory", "field": field, "message": "代码仓需要允许检索的分支白名单"})
            continue
        valid_repositories.append(repository)
    valid_log_sources = []
    for index, log_source in enumerate(intake.get("log_sources", [])):
        field = f"log_sources[{index}]"
        if not str(log_source.get("provider") or "").strip() or not str(log_source.get("environment") or "").strip():
            missing.append({"stage": "inventory", "field": field, "message": "日志源需要 provider 和 environment"})
            continue
        valid_log_sources.append(log_source)
    valid_databases = []
    for index, database in enumerate(intake.get("databases", [])):
        prefix = f"databases[{index}]"
        complete = True
        for key in ("environment", "engine", "host", "port", "database_or_service", "schema"):
            if not present(database.get(key)):
                missing.append(
                    {"stage": "inventory", "field": f"{prefix}.{key}", "message": f"数据库需要填写 {key}"}
                )
                complete = False
        if database.get("read_only") is not True:
            missing.append(
                {
                    "stage": "live_readonly",
                    "field": f"{prefix}.read_only",
                    "message": "数据库必须使用经过确认的专用只读账户",
                }
            )
            complete = False
        if complete:
            valid_databases.append(database)
    capability_ready = {
        "document_qa": bool(knowledge_sources),
        "code_analysis": bool(valid_repositories),
        "database_diagnostics": bool(valid_databases),
        "log_analysis": bool(valid_log_sources),
    }
    if "document_qa" in capabilities and not knowledge_sources:
        missing.append({"stage": "inventory", "field": "knowledge", "message": CAPABILITY_REQUIREMENTS["document_qa"]})
    if "code_analysis" in capabilities and not valid_repositories:
        missing.append({"stage": "inventory", "field": "repositories", "message": CAPABILITY_REQUIREMENTS["code_analysis"]})
    if "database_diagnostics" in capabilities and not intake.get("databases"):
        missing.append({"stage": "inventory", "field": "databases", "message": CAPABILITY_REQUIREMENTS["database_diagnostics"]})
    if "log_analysis" in capabilities and not valid_log_sources:
        missing.append({"stage": "inventory", "field": "log_sources", "message": CAPABILITY_REQUIREMENTS["log_analysis"]})

    secret_requirements = collect_secret_requirements(intake)
    required_refs = sorted(secret_requirements)
    write_text(
        workspace / "secrets" / "local-secrets.example.txt",
        "# Optional local TXT secret file. Copy to local-secrets.txt and set chmod 600.\n"
        "# Use KEY=VALUE. Never commit, upload, log, or ingest the real file.\n"
        + "\n".join(f"{key}=<set-locally>" for key in required_refs)
        + "\n",
    )
    secret_provider = intake.get("secret_provider", {})
    secret_mode = secret_provider.get("mode", "env")
    available_refs: set[str]
    if secret_mode == "env":
        available_refs = {key for key in required_refs if os.environ.get(key)}
    elif secret_mode == "file":
        raw_path = str(secret_provider.get("file_path") or "").strip()
        secret_path, _ = resolve_workspace_path(workspace, raw_path)
        available_refs, secret_error = inspect_secret_file(secret_path)
        if secret_error:
            warnings.append({"field": "secret_provider.file_path", "message": secret_error})
    else:
        available_refs = set()
        missing.append({"stage": "scaffold", "field": "secret_provider.mode", "message": "密钥方式只能是 env 或 file"})
    for ref in sorted(set(required_refs) - available_refs):
        missing.append(
            {
                "stage": secret_requirements[ref],
                "field": f"secret:{ref}",
                "message": f"请在所选密钥方式中设置 {ref}",
            }
        )

    verification = intake.get("verification", {})
    for check, message in (
        ("bot_identity", "请完成机器人身份只读验证并记录证据"),
        ("event_subscription", "请验证消息事件订阅或长连接"),
        ("test_message", "请在白名单测试群完成一次可核对的收发验收"),
        ("codex_runtime", "请完成 Codex Thread/Turn 运行时调用与话题续接验收"),
    ):
        if verification.get(check, {}).get("status") != "verified":
            missing.append({"stage": "live_readonly", "field": f"verification.{check}", "message": message})
    connector_capabilities = {"code_analysis", "database_diagnostics", "log_analysis"}
    if capabilities & connector_capabilities:
        if verification.get("read_only_connectors", {}).get("status") != "verified":
            missing.append(
                {
                    "stage": "live_readonly",
                    "field": "verification.read_only_connectors",
                    "message": "请对已启用的代码/数据库/日志连接器完成有界只读验证",
                }
            )

    missing_stages = {item["stage"] for item in missing}
    stages = {
        "ready_to_inventory": "inventory" not in missing_stages,
        "ready_to_scaffold": "scaffold" not in missing_stages,
        "ready_for_dry_run": not ({"scaffold", "dry_run"} & missing_stages),
        "ready_for_live_readonly": not ({"scaffold", "dry_run", "live_readonly", "inventory"} & missing_stages),
    }
    journey = (
        ("ready_to_inventory", "inventory", "收集一批可用资料"),
        ("ready_to_scaffold", "scaffold", "确认项目范围和运行位置"),
        ("ready_for_dry_run", "dry_run", "补齐飞书测试前配置"),
        ("ready_for_live_readonly", "live_readonly", "完成真实只读验收"),
    )
    next_stage = "complete"
    next_stage_label = "已具备正式只读运行验收条件"
    for stage_key, missing_stage, stage_label in journey:
        if not stages[stage_key]:
            next_stage = missing_stage
            next_stage_label = stage_label
            break

    def human_action(item: dict[str, str]) -> str:
        field = item["field"]
        friendly = {
            "channel.app_ready": "请确认是否已有飞书应用/机器人；如果没有，请飞书管理员创建",
            "channel.event_subscription_ready": "请让客户 IT 确认机器人能接收消息事件",
            "channel.allowed_chat_ids": "请选择一个测试群，由 Skill 解析并写入群白名单",
            "deployment.host_access_ready": "请让运维确认机器人运行主机可登录",
            "deployment.network_ready": "请让运维确认主机能访问飞书和已选项目资源",
            "deployment.maintenance_owner": "请指定一名机器人运维负责人",
        }
        if field.startswith("secret:"):
            return "请让客户 IT 按密钥示例文件在本机配置所需凭据，不要在对话中发送真值"
        if field.startswith("verification."):
            return item["message"] + "（只记录非秘密证据摘要）"
        return friendly.get(field, item["message"])

    next_actions = []
    for item in missing:
        if item["stage"] != next_stage:
            continue
        action = human_action(item)
        if action not in next_actions:
            next_actions.append(action)
        if len(next_actions) == 5:
            break
    report = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "workspace": str(workspace),
        "project": project.get("display_name", ""),
        "desired_capabilities": sorted(capabilities),
        "enabled_capabilities": sorted(
            capability for capability in capabilities if capability_ready.get(capability, True)
        ),
        "disabled_capabilities": sorted(
            capability for capability in capabilities if not capability_ready.get(capability, True)
        ),
        "stages": stages,
        "next_stage": next_stage,
        "next_stage_label": next_stage_label,
        "next_actions": next_actions,
        "missing": missing,
        "warnings": warnings,
        "secret_mode": secret_mode,
        "required_secret_names": required_refs,
        "secret_values_exposed": False,
    }
    write_json(workspace / "outputs" / "intake-report.json", report)
    lines = [
        f"# {report['project']}机器人资源评估",
        "",
        f"生成时间：{report['generated_at']}",
        "",
        "## 阶段状态",
        "",
    ]
    labels = {
        "ready_to_inventory": "可以开始资料盘点",
        "ready_to_scaffold": "可以生成机器人脚手架",
        "ready_for_dry_run": "可以进行只读试运行",
        "ready_for_live_readonly": "可以进入正式只读运行验收",
    }
    lines.extend(f"- {'✅' if value else '⬜'} {labels[key]}" for key, value in stages.items())
    lines.extend(
        [
            "",
            "## 能力状态",
            "",
            "- 当前可构建：" + ("、".join(report["enabled_capabilities"]) or "无"),
            "- 因资源缺失暂不启用：" + ("、".join(report["disabled_capabilities"]) or "无"),
        ]
    )
    lines.extend(["", "## 待补资源", ""])
    if missing:
        lines.extend(f"- **{item['stage']} / {item['field']}**：{item['message']}" for item in missing)
    else:
        lines.append("- 无")
    if warnings:
        lines.extend(["", "## 注意事项", ""])
        lines.extend(f"- **{item['field']}**：{item['message']}" for item in warnings)
    lines.extend(["", "密钥值未写入报告。", ""])
    write_text(workspace / "outputs" / "intake-report.md", "\n".join(lines))
    progress_lines = [
        f"# {report['project']}机器人搭建进度",
        "",
        f"**当前结论：{next_stage_label}。**",
        "",
        "## 四个里程碑",
        "",
        "| 里程碑 | 状态 | 意义 |",
        "| --- | --- | --- |",
        f"| 资料可盘点 | {'已就绪' if stages['ready_to_inventory'] else '待补充'} | 至少有一项所选能力的可用来源 |",
        f"| 可生成项目 | {'已就绪' if stages['ready_to_scaffold'] else '待补充'} | 已知道做什么、谁负责、运行在哪里 |",
        f"| 可进入测试 | {'已就绪' if stages['ready_for_dry_run'] else '待补充'} | 飞书应用、密钥引用、主机和网络已准备 |",
        f"| 可验收正式只读运行 | {'已就绪' if stages['ready_for_live_readonly'] else '待补充'} | 真实身份、消息和连接器均有证据 |",
        "",
        "## 现在已经能做什么",
        "",
        "- " + ("、".join(CAPABILITY_LABELS.get(item, item) for item in report["enabled_capabilities"]) or "暂无，先补一项资料来源"),
        "",
        "## 下一步只做这些",
        "",
    ]
    progress_lines.extend(f"{index}. {message}" for index, message in enumerate(next_actions, start=1))
    if not next_actions:
        progress_lines.append("1. 当前里程碑无待补项，进入下一阶段。")
    progress_lines.extend(
        [
            "",
            "## 暂未启用的可选能力",
            "",
            "- " + ("、".join(CAPABILITY_LABELS.get(item, item) for item in report["disabled_capabilities"]) or "无"),
            "",
            f"- 密钥方式：`{secret_mode}`；本页不包含任何密钥真值。",
            "- 技术字段和全部缺口见 `intake-report.md`。",
            "",
        ]
    )
    write_text(workspace / "outputs" / "搭建进度.md", "\n".join(progress_lines))
    return report


def is_sensitive(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    if lowered_parts & SKIP_PARTS:
        return True
    lowered_name = path.name.lower()
    return lowered_name == ".env" or any(fragment in lowered_name for fragment in SENSITIVE_NAME_FRAGMENTS)


def files_under(path: Path) -> Iterable[tuple[Path, Path]]:
    if path.is_file():
        if not path.is_symlink() and path.suffix.lower() in DOCUMENT_SUFFIXES and not is_sensitive(path):
            yield path, Path(path.name)
        return
    if not path.is_dir() or path.is_symlink():
        return
    for candidate in sorted(path.rglob("*")):
        relative = candidate.relative_to(path)
        if {part.lower() for part in relative.parts} & GENERATED_WORKSPACE_PARTS:
            continue
        if not candidate.is_file() or candidate.is_symlink() or is_sensitive(candidate):
            continue
        if candidate.suffix.lower() not in DOCUMENT_SUFFIXES:
            continue
        yield candidate, relative


def inspect_local_repository(root: Path, *, max_files: int = 5000) -> dict[str, Any]:
    suffix_counts: Counter[str] = Counter()
    modules: set[str] = set()
    entry_hints: list[str] = []
    files: list[str] = []
    truncated = False
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file() or candidate.is_symlink():
            continue
        relative = candidate.relative_to(root)
        if {part.lower() for part in relative.parts} & CODE_SKIP_PARTS or is_sensitive(relative):
            continue
        suffix = candidate.suffix.lower()
        if suffix not in CODE_SUFFIXES:
            continue
        files.append(str(relative))
        suffix_counts[suffix or "no_extension"] += 1
        modules.add(relative.parts[0])
        stem_lower = candidate.stem.lower()
        if any(term in stem_lower for term in ("controller", "service", "repository", "mapper", "route", "handler", "main")):
            if len(entry_hints) < 100:
                entry_hints.append(str(relative))
        if len(files) >= max_files:
            truncated = True
            break
    return {
        "file_count": len(files),
        "truncated": truncated,
        "top_level_modules": sorted(modules)[:100],
        "file_types": dict(sorted(suffix_counts.items())),
        "entry_hints": entry_hints,
        "files": files,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_entries(intake: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    knowledge = intake.get("knowledge", {})
    for section, source_type in (
        ("local_documents", "local_document"),
        ("functional_designs", "functional_design"),
    ):
        for item in knowledge.get(section, []):
            if isinstance(item, str):
                yield source_type, {"label": Path(item).name or source_type, "path": item}
            else:
                yield source_type, item


def write_first_pass_knowledge(
    workspace: Path,
    intake: dict[str, Any],
    records: list[dict[str, Any]],
    generated_at: str,
) -> None:
    project = intake.get("project", {})
    project_name = str(project.get("display_name") or "未命名项目")
    capabilities = [CAPABILITY_LABELS.get(item, item) for item in intake.get("desired_capabilities", [])]
    source_lines = []
    for record in records:
        status = record.get("snapshot_status") or record.get("metadata_status") or (
            "verified_file_hash" if record.get("sha256") else "provided_unverified"
        )
        source_lines.append(
            f"| `{record['source_id']}` | {record.get('type', '')} | {record.get('label', '')} | {status} |"
        )
    if not source_lines:
        source_lines.append("| - | - | 暂无 | pending |")
    write_text(
        workspace / "knowledge" / "wiki" / "项目总览.md",
        f"# 项目总览\n\n"
        f"> 项目：{project_name}  \n"
        f"> 首轮盘点：{generated_at}  \n"
        "> 状态：自动初稿，未标记 verified 的结论不得作为生产依据。\n\n"
        "## 业务范围\n\n"
        f"{project.get('business_scope') or '待客户确认。'}\n\n"
        "## 目标用户\n\n"
        f"{'、'.join(str(item) for item in project.get('target_roles', [])) or '待确认'}\n\n"
        "## 首期能力\n\n"
        f"{'、'.join(capabilities) or '待确认'}\n\n"
        "## 责任人\n\n"
        f"{'、'.join(str(item) for item in project.get('owners', [])) or '待确认'}\n\n"
        "## 证据概览\n\n"
        "| 来源 ID | 类型 | 名称 | 状态 |\n"
        "| --- | --- | --- | --- |\n"
        + "\n".join(source_lines)
        + "\n",
    )
    write_text(
        workspace / "knowledge" / "wiki" / "资料地图.md",
        f"# 资料地图\n\n> 生成时间：{generated_at}\n\n"
        "| 来源 ID | 类型 | 名称 | 当前状态 |\n"
        "| --- | --- | --- | --- |\n"
        + "\n".join(source_lines)
        + "\n\n云文档、数据库和日志只有在授权读取并保留证据后才能升级为 verified。\n",
    )
    deployment = intake.get("deployment", {})
    environment_lines = [
        f"- 部署方式：{deployment.get('type') or '待确认'}",
        f"- 操作系统/架构：{deployment.get('os') or '待确认'} / {deployment.get('architecture') or '待确认'}",
        f"- 服务管理：{deployment.get('service_manager') or 'none'}",
        "- 默认边界：只读、dry-run，禁止自由写库、发布、重启和删除。",
    ]
    for database in intake.get("databases", []):
        environment_lines.append(
            f"- 数据库 {database.get('environment') or '未命名'}："
            f"{database.get('engine') or '未知'} / {database.get('schema') or '未指定'} / "
            f"{'read-only' if database.get('read_only') is True else 'read-only 未验证'}"
        )
    for log_source in intake.get("log_sources", []):
        environment_lines.append(
            f"- 日志 {log_source.get('environment') or '未命名'}：{log_source.get('provider') or '未指定'}"
        )
    write_text(
        workspace / "knowledge" / "wiki" / "环境与系统边界.md",
        "# 环境与系统边界\n\n> 状态：根据问卷生成，连通性和权限仍需实测。\n\n"
        + "\n".join(environment_lines)
        + "\n",
    )
    repository_lines = []
    repository_records = [record for record in records if record.get("type") == "code_repository"]
    for repository in repository_records:
        repository_lines.append(
            f"| {repository.get('label') or '未命名'} | "
            f"{'、'.join(str(item) for item in repository.get('allowed_branches', [])) or '待确认'} | "
            f"{repository.get('local_path') or repository.get('url') or '待提供'} | provided_unverified |"
        )
    if not repository_lines:
        repository_lines.append("| - | - | 未启用代码分析 | not_applicable |")
    write_text(
        workspace / "knowledge" / "wiki" / "功能与代码索引.md",
        "# 功能与代码索引\n\n"
        "| 仓库 | 允许分支 | 位置 | 状态 |\n"
        "| --- | --- | --- | --- |\n"
        + "\n".join(repository_lines)
        + "\n\n页面→API→服务→代码→表/日志的关系必须在读取代码后补充，当前不做猜测。\n",
    )

    def write_map(filename: str, map_type: str, entries: list[dict[str, Any]]) -> None:
        lines = ["version: 1", f"map_type: {map_type}", f"generated_at: {json.dumps(generated_at)}"]
        if not entries:
            lines.append("entries: []")
        else:
            lines.append("entries:")
            for entry in entries:
                lines.append("  -")
                for key, value in entry.items():
                    lines.append(f"    {key}: {json.dumps(value, ensure_ascii=False)}")
        write_text(workspace / "knowledge" / "maps" / filename, "\n".join(lines) + "\n")

    write_map(
        "环境地图.yaml",
        "environment-map",
        [
            {
                "kind": "deployment",
                "name": deployment.get("type") or "unknown",
                "os": deployment.get("os") or "",
                "architecture": deployment.get("architecture") or "",
                "confidence": "provided_unverified",
            }
        ]
        + [
            {
                "kind": "database",
                "name": item.get("environment") or "unnamed",
                "engine": item.get("engine") or "",
                "schema": item.get("schema") or "",
                "confidence": "pending_readonly_probe",
            }
            for item in intake.get("databases", [])
        ]
        + [
            {
                "kind": "logs",
                "name": item.get("environment") or "unnamed",
                "provider": item.get("provider") or "",
                "confidence": "pending_readonly_probe",
            }
            for item in intake.get("log_sources", [])
        ],
    )
    write_map(
        "数据表结构地图.yaml",
        "data-map",
        [
            {
                "environment": item.get("environment") or "unnamed",
                "engine": item.get("engine") or "",
                "schema": item.get("schema") or "",
                "tables": [],
                "confidence": "pending_readonly_metadata",
            }
            for item in intake.get("databases", [])
        ],
    )
    write_map(
        "代码检索图.yaml",
        "code-search-map",
        [
            {
                "source_id": repository.get("source_id") or "",
                "repository": repository.get("label") or "unnamed",
                "branches": repository.get("allowed_branches", []),
                "location": repository.get("local_path") or repository.get("url") or "",
                "index_status": repository.get("index_status") or "provided_unverified",
                "file_count": repository.get("file_count", 0),
                "top_level_modules": repository.get("top_level_modules", []),
                "file_types": repository.get("file_types", {}),
                "entry_hints": repository.get("entry_hints", []),
                "confidence": "indexed" if repository.get("index_status") == "indexed_local_readonly" else "provided_unverified",
            }
            for repository in repository_records
        ],
    )
    write_map(
        "日志检索图.yaml",
        "log-search-map",
        [
            {
                "name": item.get("name") or "logs",
                "provider": item.get("provider") or "",
                "environment": item.get("environment") or "",
                "confidence": "provided_unverified",
            }
            for item in intake.get("log_sources", [])
        ],
    )
    write_map(
        "权限角色地图.yaml",
        "role-policy-map",
        [
            {
                "role": role,
                "default_access": "read_only",
                "answer_style": "diagnostic" if str(role).lower() in {"it", "developer"} else "business_language",
                "confidence": "configured",
            }
            for role in project.get("target_roles", [])
        ],
    )


def inventory_workspace(workspace: Path) -> dict[str, Any]:
    workspace = workspace.expanduser().resolve()
    intake = load_intake(workspace)
    raw_mode = intake.get("knowledge", {}).get("raw_mode", "reference")
    if raw_mode not in {"reference", "copy"}:
        raise ValueError("knowledge.raw_mode must be reference or copy")
    records: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for source_type, item in source_entries(intake):
        raw_path = str(item.get("path") or "").strip()
        if not raw_path:
            skipped.append({"type": source_type, "reason": "empty path"})
            continue
        candidate, root = resolve_workspace_path(workspace, raw_path)
        if candidate.is_symlink():
            skipped.append({"type": source_type, "path": str(candidate), "reason": "source root is a symbolic link"})
            continue
        if not root.exists():
            skipped.append({"type": source_type, "path": str(root), "reason": "path not found"})
            continue
        label = str(item.get("label") or root.name or source_type)
        label_slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", label).strip("-") or source_type
        found = False
        for path, relative in files_under(root):
            found = True
            copied_to: str | None = None
            if raw_mode == "copy":
                target = workspace / "knowledge" / "raw" / "files" / label_slug / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                copied_to = str(target.relative_to(workspace))
            records.append(
                {
                    "source_id": f"src-{len(records) + 1:05d}",
                    "type": source_type,
                    "label": label,
                    "original_path": str(path),
                    "relative_path": str(relative),
                    "raw_mode": raw_mode,
                    "copied_to": copied_to,
                    "size_bytes": path.stat().st_size,
                    "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                    "sha256": sha256(path),
                }
            )
        if not found:
            skipped.append({"type": source_type, "path": str(root), "reason": "no supported non-sensitive documents"})

    for item in intake.get("knowledge", {}).get("cloud_documents", []):
        value = {"url": item} if isinstance(item, str) else item
        records.append(
            {
                "source_id": f"src-{len(records) + 1:05d}",
                "type": "cloud_document",
                "label": str(value.get("label") or "cloud-document"),
                "url": str(value.get("url") or ""),
                "snapshot_status": "pending_authorized_fetch",
            }
        )
    repository_indexes: list[dict[str, Any]] = []
    for item in intake.get("repositories", []):
        local_path = str(item.get("local_path") or "").strip()
        record: dict[str, Any] = {
            "source_id": f"src-{len(records) + 1:05d}",
            "type": "code_repository",
            "label": str(item.get("name") or "repository"),
            "local_path": local_path,
            "url": str(item.get("url") or ""),
            "allowed_branches": item.get("allowed_branches", []),
        }
        if local_path:
            candidate, repository_root = resolve_workspace_path(workspace, local_path)
            if candidate.is_symlink():
                record["index_status"] = "rejected_symlink_root"
            elif repository_root.is_dir():
                index = inspect_local_repository(repository_root)
                record.update(
                    {
                        "local_path": str(repository_root),
                        "index_status": "indexed_local_readonly",
                        "file_count": index["file_count"],
                        "truncated": index["truncated"],
                        "top_level_modules": index["top_level_modules"],
                        "file_types": index["file_types"],
                        "entry_hints": index["entry_hints"],
                    }
                )
                repository_indexes.append(
                    {
                        "source_id": record["source_id"],
                        "name": record["label"],
                        "root": str(repository_root),
                        **index,
                    }
                )
            else:
                record["index_status"] = "local_path_not_found"
        else:
            record["index_status"] = "pending_authorized_fetch"
        records.append(record)
    for item in intake.get("databases", []):
        records.append(
            {
                "source_id": f"src-{len(records) + 1:05d}",
                "type": "database_metadata",
                "label": str(item.get("environment") or "database"),
                "engine": str(item.get("engine") or ""),
                "schema": str(item.get("schema") or ""),
                "metadata_status": "pending_readonly_probe",
            }
        )
    for item in intake.get("log_sources", []):
        records.append(
            {
                "source_id": f"src-{len(records) + 1:05d}",
                "type": "log_source",
                "label": str(item.get("name") or item.get("provider") or "logs"),
                "provider": str(item.get("provider") or ""),
                "environment": str(item.get("environment") or ""),
                "metadata_status": "pending_readonly_probe",
            }
        )

    manifest = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "raw_mode": raw_mode,
        "sources": records,
        "skipped": skipped,
    }
    write_json(workspace / "knowledge" / "raw" / "source-manifest.json", manifest)
    write_json(
        workspace / "knowledge" / "raw" / "repository-manifest.json",
        {"schema_version": 1, "generated_at": manifest["generated_at"], "repositories": repository_indexes},
    )
    yaml_lines = ["version: 1", f"generated_at: {json.dumps(manifest['generated_at'])}", "entries:"]
    for record in records:
        evidence_status = record.get("snapshot_status") or record.get("metadata_status") or (
            "verified_file_hash" if record.get("sha256") else "provided_unverified"
        )
        yaml_lines.extend(
            [
                f"  - source_id: {json.dumps(record['source_id'])}",
                f"    type: {json.dumps(record['type'])}",
                f"    label: {json.dumps(record['label'], ensure_ascii=False)}",
                f"    evidence_status: {json.dumps(evidence_status)}",
            ]
        )
    if not records:
        yaml_lines[-1] = "entries: []"
    write_text(workspace / "knowledge" / "maps" / "资料地图.yaml", "\n".join(yaml_lines) + "\n")
    write_json(
        workspace / "knowledge" / "sync" / "sync-state.json",
        {
            "schema_version": 1,
            "last_inventory_at": manifest["generated_at"],
            "sources": {record["source_id"]: record.get("sha256") for record in records},
        },
    )
    write_first_pass_knowledge(workspace, intake, records, manifest["generated_at"])
    report_lines = [
        "# 知识库质量报告",
        "",
        f"盘点时间：{manifest['generated_at']}",
        "",
        f"- 已登记来源：{len(records)}",
        f"- 已跳过来源：{len(skipped)}",
        f"- 原始资料模式：{raw_mode}",
        "- 已生成项目总览、资料地图、环境边界、代码/日志/角色地图的首轮结构化初稿。",
        "- 业务链路、表关系和代码入口仍需 Agent 读取直接证据后补充。",
        "- 数据库、日志和云文档必须在获得只读授权后补充真实元数据。",
        "",
    ]
    write_text(workspace / "knowledge" / "evidence" / "quality-report.md", "\n".join(report_lines))
    counts = Counter(str(record.get("type") or "unknown") for record in records)
    build_plan_lines = [
        "# 首轮知识库构建计划",
        "",
        f"生成时间：{manifest['generated_at']}",
        "",
        "## 已登记证据",
        "",
    ]
    if counts:
        build_plan_lines.extend(
            f"- `{source_type}`：{count} 项" for source_type, count in sorted(counts.items())
        )
    else:
        build_plan_lines.append("- 暂无可用证据，先补充资料来源。")
    build_plan_lines.extend(
        [
            "",
            "## Agent 首轮梳理顺序",
            "",
            "1. 按资料地图确认来源权威性、时效性和适用范围。",
            "2. 生成项目总览、业务与系统架构、核心业务流程。",
            "3. 从数据库元数据和样本验证中生成表结构与数据链路；不凭字段名猜关系。",
            "4. 按业务功能串联页面、接口、服务、代码、表/视图和日志关键词。",
            "5. 将冲突、未验证关系和运行时经验写入 evidence 候选区，审核后再晋级。",
            "",
            "## 验收门槛",
            "",
            "- 每个关键结论至少引用一个 `source_id`。",
            "- 关系标记为 `verified`、`probable` 或 `unverified`。",
            "- 未取得只读授权的数据库、日志和云文档保持 pending，不伪造结论。",
            "",
        ]
    )
    write_text(
        workspace / "knowledge" / "evidence" / "build-plan.md",
        "\n".join(build_plan_lines),
    )
    return {
        "status": "inventoried",
        "workspace": str(workspace),
        "source_count": len(records),
        "skipped_count": len(skipped),
        "raw_mode": raw_mode,
        "manifest": str(workspace / "knowledge" / "raw" / "source-manifest.json"),
        "build_plan": str(workspace / "knowledge" / "evidence" / "build-plan.md"),
    }


def record_verification(
    workspace: Path,
    *,
    check: str,
    status: str,
    evidence: str,
) -> dict[str, Any]:
    workspace = workspace.expanduser().resolve()
    allowed_checks = {
        "bot_identity",
        "event_subscription",
        "test_message",
        "codex_runtime",
        "read_only_connectors",
    }
    if check not in allowed_checks:
        raise ValueError("unsupported verification check")
    if status not in {"not_checked", "verified", "failed"}:
        raise ValueError("verification status must be not_checked, verified, or failed")
    evidence = evidence.strip()
    if status == "verified" and not evidence:
        raise ValueError("verified status requires a non-secret evidence reference")
    if len(evidence) > 500:
        raise ValueError("verification evidence must be 500 characters or fewer")
    if re.search(r"(?i)(?:password|secret|token|cookie|private[_ -]?key)\s*[:=]", evidence):
        raise ValueError("verification evidence must reference a result, never include a secret value")
    intake_path = workspace / "intake" / "customer-intake.json"
    intake = load_intake(workspace)
    verification = intake.setdefault("verification", {})
    verification[check] = {
        "status": status,
        "evidence": evidence,
        "updated_at": now_iso(),
    }
    write_json(intake_path, intake)
    report = assess_workspace(workspace)
    return {
        "status": "verification_recorded",
        "check": check,
        "verification_status": status,
        "ready_for_live_readonly": report["stages"]["ready_for_live_readonly"],
        "progress": str(workspace / "outputs" / "搭建进度.md"),
        "secret_values_exposed": False,
    }


def build_bot_from_workspace(workspace: Path, output: Path | None = None) -> dict[str, Any]:
    workspace = workspace.expanduser().resolve()
    report = assess_workspace(workspace)
    if not report["stages"]["ready_to_inventory"]:
        raise ValueError("尚未有可用资料，请先完成资料收集和 inventory")
    if not report["stages"]["ready_to_scaffold"]:
        raise ValueError("项目范围或部署位置尚未确认，请先查看 outputs/搭建进度.md")
    manifest_path = workspace / "knowledge" / "raw" / "source-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("generated_at") or not manifest.get("sources"):
        raise ValueError("请先运行 inventory，确认至少一项来源被登记")
    intake = load_intake(workspace)
    slug = str(intake.get("project", {}).get("slug") or "project")
    bot_output = (output or (workspace / "bot")).expanduser().resolve()
    scaffold_script = Path(__file__).resolve().with_name("scaffold_project_bot.py")
    command = [
        sys.executable,
        str(scaffold_script),
        "--intake",
        str(workspace / "intake" / "customer-intake.json"),
        "--output",
        str(bot_output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise ValueError(f"机器人项目生成失败：{detail}")
    try:
        scaffold_result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("机器人生成器未返回有效 JSON") from exc
    result = {
        "status": "bot_project_created",
        "workspace": str(workspace),
        "bot_output": str(bot_output),
        "slug": slug,
        "enabled_capabilities": report["enabled_capabilities"],
        "disabled_capabilities": report["disabled_capabilities"],
        "ready_for_dry_run": report["stages"]["ready_for_dry_run"],
        "ready_for_live_readonly": False,
        "scaffold": scaffold_result,
    }
    write_json(workspace / "outputs" / "build-result.json", result)
    write_text(
        workspace / "outputs" / "机器人交付说明.md",
        f"# {report['project']}机器人交付说明\n\n"
        f"- 机器人项目：`{bot_output}`\n"
        f"- 已带入能力：{'、'.join(CAPABILITY_LABELS.get(item, item) for item in report['enabled_capabilities']) or '无'}\n"
        f"- 暂未启用：{'、'.join(CAPABILITY_LABELS.get(item, item) for item in report['disabled_capabilities']) or '无'}\n"
        f"- 密钥方式：`{report['secret_mode']}`（未复制密钥真值）\n"
        "- 当前是安全脚手架，不等于已上线。\n"
        "- 下一步：完成飞书/Codex 真实适配器、测试群收发、只读连接器和重启恢复验收。\n",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a customer onboarding workspace")
    init_parser.add_argument("--name", required=True)
    init_parser.add_argument("--slug", default="", help="Optional ASCII slug; derived automatically when omitted")
    init_parser.add_argument("--output", default="", help="Defaults to ./outputs/<slug>-bot-workspace")
    init_parser.add_argument("--channel", choices=("feishu", "lark", "dingtalk", "wecom", "web"), default="feishu")
    init_parser.add_argument("--deployment", choices=("local", "launchd", "systemd", "docker", "hosted"), default="local")
    init_parser.add_argument("--secret-mode", choices=("env", "file"), default="env")
    init_parser.add_argument("--raw-mode", choices=("reference", "copy"), default="reference")
    init_parser.add_argument(
        "--capabilities",
        default="document_qa",
        help="Comma-separated: document_qa,code_analysis,database_diagnostics,log_analysis",
    )

    for command in ("assess", "status", "inventory"):
        child = subparsers.add_parser(command)
        child.add_argument("--workspace", required=True)

    verify_parser = subparsers.add_parser("mark-check", help="Record a non-secret live verification result")
    verify_parser.add_argument("--workspace", required=True)
    verify_parser.add_argument(
        "--check",
        required=True,
        choices=("bot_identity", "event_subscription", "test_message", "codex_runtime", "read_only_connectors"),
    )
    verify_parser.add_argument("--status", required=True, choices=("not_checked", "verified", "failed"))
    verify_parser.add_argument("--evidence", default="", help="Short non-secret result or evidence reference")

    build_parser = subparsers.add_parser("build-bot", help="Generate a bot project from a ready workspace")
    build_parser.add_argument("--workspace", required=True)
    build_parser.add_argument("--output", default="", help="Defaults to <workspace>/bot")

    args = parser.parse_args()
    try:
        if args.command == "init":
            slug = derive_slug(args.name.strip(), args.slug)
            output = (
                Path(args.output)
                if args.output.strip()
                else Path.cwd() / "outputs" / f"{slug}-bot-workspace"
            )
            result = initialize_workspace(
                output,
                name=args.name.strip(),
                slug=slug,
                channel=args.channel,
                deployment=args.deployment,
                secret_mode=args.secret_mode,
                raw_mode=args.raw_mode,
                desired_capabilities=parse_capabilities(args.capabilities),
            )
        elif args.command in {"assess", "status"}:
            result = assess_workspace(Path(args.workspace))
        elif args.command == "inventory":
            result = inventory_workspace(Path(args.workspace))
        elif args.command == "mark-check":
            result = record_verification(
                Path(args.workspace),
                check=args.check,
                status=args.status,
                evidence=args.evidence,
            )
        else:
            build_output = Path(args.output) if args.output.strip() else None
            result = build_bot_from_workspace(Path(args.workspace), build_output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
