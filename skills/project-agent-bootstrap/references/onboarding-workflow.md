# Guided Customer Onboarding

Use this workflow when the customer begins with a goal rather than a technical specification.

## First response

Confirm the intended outcome, then ask no more than three business-language questions:

1. Project name, the problem the bot should solve, and who will use it.
2. The smallest useful first version and which materials are already accessible. Default to document Q&A when the customer is unsure.
3. Whether a Feishu app and a local/customer/hosted machine already exist; “不知道，需要 IT 协助” is a valid answer.

Derive the internal slug and default workspace path; never ask a non-technical customer for a slug, JSON field, package name, or command line. Use the answers to generate the onboarding workspace, update `customer-intake.json` on the customer's behalf, and show `outputs/搭建进度.md`. Do not ask for every connector when the capability is not requested.

## Adaptive resource form

Resolve facts from local files and accessible links before asking the customer. For every field, record one of:

- `ready`: discovered and verified;
- `provided_unverified`: supplied but not tested;
- `missing_required`: blocks the selected stage;
- `missing_optional`: disables one optional capability;
- `not_applicable`: not needed for this bot.

Ask for missing items in small related batches.

The customer-facing form is `intake/资源收集表.md`. It must accept “不知道” and must not require the customer to edit JSON. `intake/资源填写示例.json` is for the Agent or customer IT, not the first-line user.

### Project and roles

- Business scope and out-of-scope topics
- Owner and maintenance owner
- User roles and answer language
- Whether business and IT users require different permissions or answer formats

### Knowledge sources

- Local document folders
- Functional design, operation manual, training material, issue history, and database design
- Feishu/Lark or other cloud-document links
- Authoritative-source order and freshness owner
- Raw material mode: reference in place or copy into `knowledge/raw/files`

### Databases

- Environment label, engine, host, port, database/service, schema
- Dedicated read-only principal and secret key names
- VPN/network dependency, row limit, timeout, and sensitive-column redaction
- Metadata access and read-only session support

### Code and logs

- Repository URL or local path, allowed branches, and read-only authentication readiness
- Log provider, environment, namespace/workload, allowed log roots, time window, and redaction
- Whether remote-ref synchronization is permitted

### Channel and deployment

- Bot application readiness, event subscription, scopes, and chat allowlist
- Host OS/architecture, service manager, working directory, network, monitoring, backup, and rollback
- Secret method: `env` or local TXT file

## Secret collection

Never collect secret values in chat or store them in intake JSON.

For `env`, record only required variable names and verify that each name is set.

For `file`, use a local file such as `secrets/local-secrets.txt`:

```text
FEISHU_APP_ID=<set-locally>
FEISHU_APP_SECRET=<set-locally>
DB_UAT_USER=<set-locally>
DB_UAT_PASSWORD=<set-locally>
```

The real file must be ignored by Git, excluded from source inventory and generated artifacts, not be a symbolic link, and use POSIX mode `0600`. Never echo values during validation.

## Capability degradation

- Documents only: deploy a document/knowledge assistant; database, code, and log tools stay disabled.
- Documents plus code: enable implementation and error-path analysis, but do not claim live data diagnosis.
- Read-only database ready: enable bounded metadata and query tools for allowlisted environments.
- Read-only logs ready: enable bounded diagnostic log search.
- Missing channel credentials: continue knowledge and scaffold construction, but stop before dry-run messaging.

End every onboarding turn with the current milestone, completed items, disabled optional capabilities, and at most five next actions. Use Chinese labels for a Chinese-speaking customer; keep technical field names in the detailed report only.

Do not report live readiness from questionnaire answers alone. `ready_for_dry_run` means configuration is sufficient to attempt a controlled test. `ready_for_live_readonly` requires recorded evidence for bot identity, event subscription, a test message, the Codex Thread/Turn runtime, and each enabled read-only connector.
