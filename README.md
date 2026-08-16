# AI-WORK

Reusable AI project automation skills and secure agent starter templates.

## Skills

### project-agent-bootstrap

Build, modernize, or audit a project-specific intelligent bot with Feishu/Lark and Codex.

**Capabilities:**

- **Intake** - Collect minimum project facts (Feishu, databases, repos, hosts) via a fillable blueprint
- **Scaffold** - Generate a security-first bot starter from `assets/project-bot-starter/`
- **Integrate** - Connect Feishu, Codex, databases, code repos, logs, and document delivery
- **Audit** - Inspect an existing bot and rank changes by safety, reliability, and maintainability
- **Deploy** - Validate and install a service only after explicit authorization
- **Publish** - Upload sanitized reusable Skill or scaffold to a selected GitHub destination

**Quick start:**

```bash
git clone https://github.com/FOX-WSW/AI-WORK.git
cd AI-WORK/skills/project-agent-bootstrap

python scripts/scaffold_project_bot.py \
  --name "Example Project Bot" \
  --slug "example-project-bot" \
  --output "./output" \
  --service launchd \
  --databases oracle
```

**Structure:**

```
skills/project-agent-bootstrap/
├── SKILL.md                    # Skill definition and workflow
├── scripts/
│   ├── scaffold_project_bot.py # Generate a new bot starter
│   └── validate_scaffold.py    # Validate scaffold hygiene
├── references/
│   ├── architecture.md          # Module boundaries and migration order
│   ├── security-boundaries.md   # Security defaults and tool gating
│   ├── intake-checklist.md      # Required project facts
│   └── acceptance-matrix.md     # Deployment readiness criteria
├── agents/
│   └── openai.yaml              # Agent runtime config
└── assets/
    └── project-bot-starter/     # Reusable starter template (src, tests, service, config)
```

**Safety defaults:**

- Non-empty chat allowlist required; fail startup if absent
- `dry_run=true` and `allow_real_writes=false` by default
- Read-only database principals only
- Credentials stored only in environment variables or secret manager
- Approval bound to requester, topic, operation hash, expiry, and one-time consumption
- Production writes disabled by default

## License

MIT
