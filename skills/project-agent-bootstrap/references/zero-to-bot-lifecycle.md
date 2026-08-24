# Zero-to-Bot Lifecycle

Use this reference when creating a complete project bot or demonstrating that the method can be repeated beyond one knowledge base or one customer case.

## Lifecycle contract

The Skill covers nine connected stages. A stage may be revisited, but it must not be silently omitted.

| Stage | Required work | Minimum artifact | Gate before continuing |
|---|---|---|---|
| 1. Scenario and boundaries | Identify users, priority scenarios, business value, supported and unsupported requests, environments, and read/write boundaries. | Scenario list, non-goals, success criteria | The first release has a bounded purpose and an owner. |
| 2. Resource readiness | Inventory documents, cloud sources, databases, APIs, repositories, logs, channel, deployment host, permissions, and secret method. | Source inventory, resource-gap report, readiness status | Missing resources are explicit; optional gaps do not block a smaller safe scope. |
| 3. Knowledge and evidence | Build provenance-preserving `raw/wiki/maps/evidence/sync`, source authority, vocabulary, navigation maps, and RAG/live-data routing. | Knowledge workspace, evidence gaps, retrieval evaluation plan | Stable knowledge and live facts have different retrieval paths. |
| 4. Secure scaffold | Generate configuration, ingress, state, Agent runtime, capabilities, policy, delivery, operations, and observability boundaries. | Runnable scaffold with `scaffold_only=true` | Fail-closed startup and non-secret configuration validation pass. |
| 5. Channel and identity | Connect the supported channel and restore sender, group, mention, reply, thread, attachment references, time, and idempotency key. | Channel contract test and identity-policy mapping | Duplicate, unauthorized, malformed, and out-of-order messages are covered. |
| 6. Bounded tools | Connect only ready documents, database/API, repository, log, build, or artifact adapters with time, row, branch, namespace, and environment bounds. | Adapter configuration and contract-test evidence | Production defaults to read-only; model context contains only authorized results. |
| 7. Policy and delivery | Enforce minimum permissions, refusal/degradation, sensitive-content checks, approval, FinalDelivery, persistence, and delivery status. | Policy matrix, audit fields, delivery-state tests | Generated, allowed, accepted, visible, failed, and recovered states remain distinct. |
| 8. Validation and handoff | Run unit, contract, fault, security, regression, dry-run, rollback, and operator checks. | Acceptance matrix, validation logs, runbook, rollback and handoff checklist | Claims match evidence; mock or fixture results are not described as live deployment. |
| 9. Operation and evolution | Track answer quality, tool success, silence, escalation, freshness, feedback, candidate knowledge, versions, and specialized Skills. | Operations ledger, review queue, update plan | Runtime experience requires review before it becomes authoritative knowledge. |

## Reuse boundary

Reuse these across projects:

- guided questions and readiness gates;
- knowledge/evidence folder contracts and routing rules;
- secure architecture, configuration schemas, adapters, and tests;
- permission, approval, delivery, observability, rollback, and handoff templates;
- evaluation metrics, candidate-knowledge governance, and contest evidence packaging.

Replace these for each project:

- customer documents and raw data;
- business terms, object relationships, fields, statuses, and rules;
- accounts, endpoints, groups, roles, repositories, environments, and credentials;
- project-specific acceptance thresholds and operational ownership.

Knowledge-base construction is Stage 3. It is necessary for many project bots, but it does not replace channel integration, deterministic permissions, live tool contracts, delivery reliability, testing, deployment, handoff, or ongoing governance.

## Reporting contract

For a full lifecycle request, report every stage as `not_started`, `in_progress`, `ready`, `blocked`, or `verified`. Include the evidence reference and next safe action. Never summarize the whole project as “ready” because only the knowledge workspace or scaffold exists.
