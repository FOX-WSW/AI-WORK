# Project Bot Factory Contest Demo

Use this profile only when the user wants a competition rehearsal, a reproducible product demonstration, or evidence that `project-agent-bootstrap` can create a second project bot. Ordinary onboarding should continue to use `onboarding-workflow.md`.

## Product claim

Present the Skill as a **project bot factory**, not as another single-purpose chatbot:

> A non-technical project colleague starts with one sentence and incomplete materials. The Skill turns them into a traceable knowledge workspace, a fail-closed bot project, a resource-gap report, and verifiable handoff evidence.

The competition loop is:

`one-sentence intent -> guided intake -> bounded inventory -> raw/wiki/maps/evidence/sync -> secure bot scaffold -> validation and tests -> evidence pack -> human decision about live integration`

The reusable method is the product. A manufacturing project may be the golden case, but customer-specific facts must remain in the case fixture or generated workspace.

## Run the reproducible golden case

From the Skill directory, choose a new output directory and run:

```bash
python scripts/run_contest_demo.py \
  --case assets/contest-demo-case \
  --output "/absolute/new/demo-output"
```

The runner performs only local, reversible work. It:

1. checks that the fixture contains no symlinks or common secret/private-address patterns;
2. initializes a guided onboarding workspace;
3. copies the sanitized documents and sample repository into that workspace;
4. applies the fixture's non-secret intake answers;
5. runs assessment, source inventory, knowledge-map generation, and bot scaffolding;
6. validates the generated scaffold and runs its unit tests;
7. emits `evidence/contest-evidence.json`, `evidence/评委摘要.md`, logs, and file hashes.

The output must preserve:

- `scaffold_only=true`;
- `deployment_ready=false`;
- `external_write_performed=false`;
- missing live Feishu/Codex/deployment checks as explicit limitations.

Do not call the fixture run a live AI result. It proves deterministic mechanics and provides a network-independent fallback.

## Live demonstration

For the live path, invoke the Skill normally and start with:

> 我想部署一个自己的项目机器人，但我不懂技术配置。

Use a new isolated output directory. Let the user answer the first business questions, then use a sanitized copy of the same materials. Show these checkpoints instead of narrating internal code:

1. `outputs/搭建进度.md`: what the customer has supplied and what is still missing;
2. `knowledge/wiki/项目总览.md` and `knowledge/maps/代码检索图.yaml`: traceable knowledge and bounded navigation;
3. `bot/CUSTOMER_HANDOFF.md`: what the generated project can and cannot do;
4. `.project-agent-bootstrap.json`: `scaffold_only` and `deployment_ready` truth;
5. the validator and generated-project test results.

If the live model, network, or tool path fails, switch to the golden-case output and label it as an offline fallback. Never edit the evidence pack to simulate a successful live run.

## Five-minute judging story

- **0:00-0:40 — pain:** project bots require repeated coordination across requirements, knowledge, security, code, and deployment.
- **0:40-1:20 — input:** a colleague provides one sentence and project materials without editing JSON or command arguments.
- **1:20-2:30 — transformation:** show resource readiness, source fingerprints, Wiki, and navigation maps.
- **2:30-3:40 — output:** show the generated fail-closed bot project, handoff, validation, and tests.
- **3:40-4:30 — boundary:** explain why a generated scaffold is not reported as deployed and why real writes remain disabled.
- **4:30-5:00 — scalability:** replace the fixture with another project's materials and repeat the same method.

## Evidence rules

- Separate live-run evidence from fixture-run evidence.
- Use measured duration only for the exact recorded run; do not convert it into claimed labor savings.
- A passing offline demo does not prove answer accuracy, production readiness, or live delivery.
- Real Feishu creation, messages, deployment, repository publication, permissions, and other external changes still require the authorization applicable to the target environment.
- Preserve the source revision, fixture hashes, generated manifest, validation logs, and skipped live checks.
