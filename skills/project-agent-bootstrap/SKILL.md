---
name: project-agent-bootstrap
description: Guide a non-technical customer from “I want my own bot” through adaptive resource intake, raw/wiki/maps knowledge-base construction, secure project-bot scaffolding, integration, validation, and authorized deployment. Use when a user wants to create, reproduce, modernize, audit, or deploy a project bot from local documents, cloud documents, databases, code repositories, logs, and project environments.
---

# Project Agent Bootstrap

Turn incomplete customer materials into a traceable knowledge base and a safely deployable project bot. From the customer's perspective this is one guided Skill; internally keep onboarding, knowledge building, bot generation, deployment, and knowledge maintenance as separate modes.

## Route the request

- `onboard`: the user says “我想部署一个自己的机器人” or cannot provide a technical specification. Discover what already exists, ask only for missing decisions, and produce a resource-gap report.
- `build-knowledge`: inventory original sources, create the `raw/wiki/maps/evidence/sync` structure, and perform the first evidence-based knowledge pass.
- `build-bot`: generate or extend the project-bot starter and connect only the capabilities supported by ready resources.
- `integrate`: connect messaging, Codex, cloud documents, databases, repositories, logs, or artifact delivery.
- `audit`: inspect an existing bot and rank safety, reliability, knowledge, and deployment gaps.
- `deploy-and-operate`: validate, install, verify, monitor, roll back, or maintain a service only after the user authorizes the external changes.
- `publish`: publish only sanitized generic Skill or scaffold files to an explicitly selected destination.

Combine modes when needed, but report a separate readiness state for inventory, scaffold, dry-run, and live read-only operation.

## Start with guided onboarding

When the user asks to deploy a bot, do not begin with a long technical interrogation. First inspect the available workspace and links, then follow [references/onboarding-workflow.md](references/onboarding-workflow.md).

Ask no more than three business-language questions in the first turn and accept “不知道，需要 IT 协助”. Infer the slug, package name, and default workspace path; never ask a non-technical customer to edit JSON or supply command-line parameters. Default the first version to document Q&A when the customer is unsure, then add code, database, and log capabilities only when requested. Collect project scope, users and roles, channel, deployment host, local and cloud documents, functional designs, database environments, repositories, logs, cloud services, and safety boundaries in later small batches. Missing optional resources must not block a document-only bot.

The current bundled runtime starter targets Feishu. Other channel choices may be captured during onboarding for future integration, but they must remain `ready_to_scaffold=false` until a channel-specific adapter and live acceptance tests are added. Do not silently generate a Feishu-shaped project for another platform.

Never ask the user to paste secret values into chat. Two secret methods are supported:

- `env`: values are injected through environment variables.
- `file`: values are stored locally in a TXT file using `KEY=VALUE`, normally `secrets/local-secrets.txt`. The file must be excluded from Git and knowledge ingestion, must not be a symbolic link, and on POSIX must have mode `0600`.

Only secret names and readiness states may appear in reports.

Initialize the onboarding workspace with the bundled script:

```bash
python scripts/onboard_project_bot.py init \
  --name "示例项目" \
  --channel feishu \
  --deployment systemd \
  --secret-mode env \
  --raw-mode reference \
  --capabilities document_qa
```

After the non-secret intake file is completed:

```bash
python scripts/onboard_project_bot.py assess --workspace "/absolute/output/path"
python scripts/onboard_project_bot.py status --workspace "/absolute/output/path"
python scripts/onboard_project_bot.py inventory --workspace "/absolute/output/path"
```

`assess` is expected to report missing resources during early onboarding; incompleteness is not an execution failure. Show the customer `outputs/搭建进度.md` rather than exposing raw field names. Update `customer-intake.json` on the customer's behalf after each answer batch.

## Build the knowledge base before the live bot

Read [references/knowledge-build-workflow.md](references/knowledge-build-workflow.md) before performing first-round semantic organization. Preserve original evidence and provenance. Do not invent table relationships, business statuses, code entry points, or source priority.

The standard knowledge layout is:

```text
knowledge/
├── raw/       original files or references plus source manifest
├── wiki/      human-readable project knowledge
├── maps/      deterministic source/data/business/code/log/role navigation
├── evidence/  quality, conflict, uncertainty, and verification records
└── sync/      freshness and incremental-update state
```

Prefer bounded keyword and relationship-map retrieval for rapidly changing project documents and code. Use semantic retrieval only when the source is stable and it materially improves recall. The most useful navigation chain is:

`business function -> page -> API -> service -> code -> table/view -> log keyword -> known issue`

After `inventory`, produce a useful first pass rather than returning empty placeholders: populate the project overview, source map, environment boundary, repository index, and role/code/log maps from direct intake or file evidence. Clearly mark questionnaire-only facts as `provided_unverified`; never invent business flows, table relationships, or code entry points. Runtime experience must enter a candidate area first. Only reviewed evidence may update authoritative Wiki or maps. Keep scheduled source synchronization separate from answering user questions.

## Generate the bot safely

Use the existing scaffold generator after `ready_to_scaffold=true`:

```bash
python scripts/scaffold_project_bot.py \
  --name "示例项目智能机器人" \
  --slug "example-project-bot" \
  --output "/absolute/bot/path" \
  --service systemd \
  --secret-mode env \
  --databases oracle \
  --database-env UAT:oracle
```

When the onboarding workspace already exists, prefer importing it so the bot receives the selected secret mode, deployment settings, database environments, and knowledge tree:

```bash
python scripts/scaffold_project_bot.py \
  --intake "/absolute/workspace/intake/customer-intake.json" \
  --output "/absolute/bot/path"
```

For a non-technical customer, prefer the one-step workspace command after both inventory and scaffold gates pass:

```bash
python scripts/onboard_project_bot.py build-bot --workspace "/absolute/workspace"
```

The generated starter is intentionally fail-closed and remains `scaffold_only=true`. It includes `CUSTOMER_HANDOFF.md` so a new colleague can see what is complete and what still blocks launch. It is not a live bot until real adapters, a `serve` entrypoint, and authorized live tests exist. Enable only capabilities whose resource and secret checks pass. Keep business and IT answer styles and permissions distinct when both roles use the same bot.

Follow [references/architecture.md](references/architecture.md) for module boundaries. Put customer-specific facts in instance configuration and the generated knowledge base, never in the reusable Skill.

## Keep hard safety boundaries

Read [references/security-boundaries.md](references/security-boundaries.md) before adding database, log, cloud, deployment, or write tools.

- Require non-empty chat and environment allowlists for live operation.
- Default to `dry_run=true`, `allow_real_writes=false`, and dedicated read-only accounts.
- Treat SQL validation as defense in depth, not as a substitute for database grants.
- Allowlist schemas, repositories, branches, namespaces, file roots, channels, and delivery targets.
- Bind any approved write to requester, topic, exact operation hash, environment, expiry, and one-time use.
- Persist the answer before external delivery; preserve one topic to one Agent thread and FIFO ordering.
- Never place secret files, state, logs, attachments, internal addresses, or customer raw materials in a reusable package or public repository.

## Validate by stage

Run:

```bash
python /path/to/skill-creator/scripts/quick_validate.py /path/to/project-agent-bootstrap
python scripts/validate_scaffold.py /path/to/generated-project
PYTHONPATH=/path/to/generated-project/src python -m unittest discover -s /path/to/generated-project/tests -v
```

Then follow [references/acceptance-matrix.md](references/acceptance-matrix.md). Do not collapse these states:

- `ready_to_inventory`
- `ready_to_scaffold`
- `ready_for_dry_run`
- `ready_for_live_readonly`
- `ready_for_write_capability`

Do not claim deployment readiness when only the onboarding workspace, knowledge skeleton, scaffold, or mocked tests passed.

Questionnaire booleans are configuration claims, not live evidence. Record actual checks with `mark-check` only after performing them, and store a short non-secret evidence reference:

```bash
python scripts/onboard_project_bot.py mark-check \
  --workspace "/absolute/workspace" \
  --check bot_identity \
  --status verified \
  --evidence "test-tenant identity probe passed at 2026-08-20 14:30 +08:00"
```

## Deploy and hand off

Before installing or restarting a service, show the resolved non-secret plan and intended external effects, obtain authorization, back up state, and verify rollback. A hosted server, customer server, local computer, or cloud host is acceptable only after network, runtime, secret injection, maintenance ownership, monitoring, and recovery checks pass.

Return:

- completed non-secret intake and missing-resource report;
- knowledge workspace path, source manifest, generated Wiki/maps, and unresolved evidence gaps;
- generated bot path and enabled/disabled capabilities;
- required secret names without values and the selected `env` or TXT-file method;
- validation evidence and live checks not performed;
- deployment, status, stop, backup, and rollback instructions when deployment was requested.
