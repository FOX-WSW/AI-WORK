# Acceptance Matrix

## Static and unit checks

- Skill metadata validation passes.
- Onboarding initialization creates intake, secret example, `raw/wiki/maps/evidence/sync`, and start instructions without embedding a secret.
- Intake assessment reports missing resources by stage and keeps optional capability gaps separate from hard blockers.
- Source inventory excludes `.env`, real secret TXT files, symlinks, Git internals, and credential-like filenames.
- File secret mode rejects missing, symlinked, malformed, placeholder, duplicate-key, or non-0600 files on POSIX.
- Generated scaffold contains no unresolved template tokens.
- Generated scaffold reports `scaffold_only=true` and `deployment_ready=false` until real adapters and live tests exist.
- Secret scan finds no credential values or internal addresses.
- Configuration rejects an empty live chat allowlist.
- Live configuration rejects an implicit project root and a state path outside its approved root.
- Defaults are `dry_run=true` and `allow_real_writes=false`.
- SQL policy rejects DML/DDL, multiple statements, locking clauses, and known side-effect packages.
- Topic state deduplicates the same event ID and the same Feishu message ID.
- Topic state preserves FIFO ordering.
- Delivery cannot become `delivered` without a verifiable external message ID.
- Approval records bind exact parameters and cannot execute twice.

## Guided onboarding checks

- A customer saying only “我想部署一个自己的机器人” receives no more than the initial routing questions before a tailored resource form.
- The customer is never asked for a slug, package name, JSON field, or output path; Chinese-only project names get a deterministic safe slug.
- Initialization defaults to a document-Q&A MVP unless the customer explicitly selects more capabilities.
- Relative document paths resolve against the onboarding workspace and a symlinked source root is rejected.
- `outputs/搭建进度.md` gives Chinese milestone status and no more than five next actions.
- A documents-only customer can reach inventory/scaffold readiness with database, code, and log capabilities explicitly disabled.
- An incomplete customer receives a usable gap report rather than a false deployment failure.
- The generated source manifest preserves path, hash, modification time, type, and raw copy/reference mode.
- Wiki and map conclusions cite source IDs and distinguish verified, probable, and unverified relationships.
- Runtime experience cannot update authoritative knowledge without review.
- Questionnaire answers alone cannot produce `ready_for_live_readonly=true`; bot identity, event subscription, test message, Codex runtime, and enabled connector evidence records are required.
- A ready inventoried workspace can generate one bot project with `build-bot`, including `CUSTOMER_HANDOFF.md`.
- A non-Feishu channel and an unsupported service manager remain inventory-only instead of being reported as scaffold-ready.

## Fault injection

- Duplicate Feishu event
- Event stream disconnect and reconnect
- Service restart before and after answer persistence
- Codex timeout before any tool call
- Codex timeout after successful tools but before synthesis
- Database timeout, permission denial, and malformed SQL
- Feishu reply timeout, 429, ambiguous result, and withdrawn source message
- Artifact upload succeeds but local acknowledgement is lost
- State database locked or temporarily unavailable
- Secret/authentication revoked during operation

Every path must become either a verified success, a scheduled retry, a cancellation, or a visible failure. No message may remain silently `processing`.

## Live read-only checks

Perform only when authorized:

- Verify bot identity and event subscription.
- Resolve target chat IDs and confirm the allowlist.
- Receive one controlled dry-run mention without sending a reply.
- Send one controlled reply in a test chat.
- Run one bounded query per configured read-only data source.
- Fetch one bounded log sample.
- Restart the service with an empty queue and verify readiness.
- Restart during a synthetic turn and verify recovery.

## Production readiness evidence

Record:

- exact source revision;
- non-secret configuration snapshot;
- validation commands and results;
- live checks performed and skipped;
- service status and health output;
- state backup path;
- rollback command;
- secret owner and rotation procedure;
- enabled capability list.
