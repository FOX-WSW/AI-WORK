# AI-WORK

可复用的 AI 项目自动化 Skill 与安全机器人脚手架。

## project-agent-bootstrap

`project-agent-bootstrap` 面向没有机器人搭建经验的新项目同事。用户只需要说“我想部署一个自己的机器人”，Skill 会把从场景澄清、资源盘点到机器人搭建、接入、验证、部署交接和持续运营的零到一过程串成一条闭环。知识库构建是其中一个关键环节，不是全部能力。

### 能力

- 引导式资源收集：项目范围、用户角色、飞书、部署主机、本地/云文档、数据库、代码仓库、日志和安全边界。
- 小白友好：首轮最多询问 3 个业务问题，允许回答“不知道，需要 IT 协助”。
- 两种凭据方式：环境变量，或本机 `KEY=VALUE` TXT 文件（不进入 Git，POSIX 权限要求 `0600`）。
- 第一轮知识梳理：生成 `raw/wiki/maps/evidence/sync` 架构、资料地图、环境地图、表结构地图、业务链路图、代码检索图和日志检索图。
- 完整机器人工程：生成消息入口、状态机、Agent 运行时、数据/日志/代码适配器、权限策略、安全投递、可观测和运维边界。
- 上线前后闭环：覆盖契约/故障/安全/回归测试、dry-run、部署回滚、项目交接、运行指标、候选经验和持续更新。
- 安全脚手架：默认只读、`dry_run=true`、`allow_real_writes=false`，飞书和环境白名单缺失时拒绝启动。
- 分阶段验收：区分资料盘点、脚手架、试运行、真实只读运行和写能力，不把模拟测试等同于上线完成。

### 比赛闭环：项目机器人搭建工厂

参赛时可把 Skill 本身作为产品：普通项目同事只说一句“我想部署自己的项目机器人”，Skill 按九步完成场景与边界、资源盘点、知识与证据、工程脚手架、通道与身份、工具接入、权限与投递、测试交接、运营进化。莫干山是黄金案例，Skill 是完整方法的复用证明。

仓库提供一个完全脱敏、可离线复现的家居制造样板：

```bash
cd AI-WORK/skills/project-agent-bootstrap
python scripts/run_contest_demo.py \
  --case assets/contest-demo-case \
  --output "/absolute/new/demo-output"
```

生成结果包含客户搭建进度、知识库、机器人安全脚手架、生成项目测试、校验日志、文件哈希和评委摘要。离线样板会明确标记为 `offline_reproducible_fixture`，并保持 `scaffold_only=true`、`deployment_ready=false`，不会冒充现场 AI 或已经上线。

### 快速开始

```bash
git clone https://github.com/FOX-WSW/AI-WORK.git
cd AI-WORK/skills/project-agent-bootstrap

python scripts/onboard_project_bot.py init \
  --name "示例项目" \
  --channel feishu \
  --deployment systemd \
  --secret-mode env \
  --raw-mode reference \
  --capabilities document_qa

python scripts/onboard_project_bot.py assess --workspace "/absolute/workspace/path"
python scripts/onboard_project_bot.py inventory --workspace "/absolute/workspace/path"
python scripts/onboard_project_bot.py build-bot --workspace "/absolute/workspace/path"
```

不确定参数时，不需要自己执行命令；直接让 Codex 使用该 Skill，并说：

> 我想部署一个自己的机器人。

### 目录

```text
skills/project-agent-bootstrap/
├── SKILL.md
├── agents/
├── scripts/
│   ├── onboard_project_bot.py
│   ├── run_contest_demo.py
│   ├── scaffold_project_bot.py
│   └── validate_scaffold.py
├── references/
├── tests/
├── assets/contest-demo-case/
└── assets/project-bot-starter/
    ├── knowledge/
    ├── secrets/
    ├── src/
    └── tests/
```

### 安全说明

- 不要在聊天、代码、知识库或 GitHub 中粘贴真实密码、Token、Cookie、私钥或生产连接串。
- TXT 凭据文件必须保留在客户本机并排除于 Git；仓库只提供示例文件。
- 生成的项目默认标记为 `scaffold_only=true`、`deployment_ready=false`。
- 只有真实飞书事件、Codex 运行、数据源连接、故障恢复和回滚验证完成后，才能声明具备上线条件。

## License

MIT
