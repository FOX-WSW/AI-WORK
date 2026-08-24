# Evidence-Based Knowledge Build

Use this workflow after the resource inventory exists.

## Preserve source truth

- Keep an immutable source manifest with source type, original location, hash, modification time, and snapshot/copy status.
- `raw_mode=reference` records originals in place. `raw_mode=copy` copies supported non-sensitive documents into `knowledge/raw/files` while preserving relative paths.
- Never ingest `.env`, secret TXT files, key material, cookies, credentials, state databases, logs containing authentication headers, or Git internals.
- Cloud documents, database metadata, code refs, and logs require explicit authorized fetches; an unverified link is only a pending source.

## First-round organization

The deterministic inventory step must immediately populate an evidence-limited first draft of project overview, source map, environment boundary, repository index, and role/code/log maps. Do not leave every file as an empty heading. Treat form-only facts as `provided_unverified`; a later Agent semantic pass upgrades only conclusions supported by direct evidence.

Produce these Wiki pages from direct evidence:

1. Project overview and scope
2. Business and system architecture
3. Core business processes and status transitions
4. Environment and access boundaries
5. Core business data model
6. Function and code index
7. Reviewed common problems and handling experience
8. Source map

Create these deterministic maps:

- Source map: source, owner, authority, freshness, scope, and evidence location
- Environment map: DEV/SIT/UAT/PROD boundaries and reachable systems
- Data map: business object, table/view, key, relation, schema, and verification sample
- Business-flow map: node, state, predecessor, successor, system, evidence
- Function-entry map: business term, UI entry, route, API, role, and screenshot/document evidence
- Code-search map: repository, branch, module, controller, service, mapper/query, table, and error keyword
- Log-search map: environment, service, workload/container, log root, API/error keywords, and time format
- Glossary: business term, aliases, table fields, code terms, and excluded meanings
- Role-policy map: role, allowed capabilities, answer style, sensitive evidence, and approval owner

## Relationship rules

Never infer a production relationship from similar names alone. Mark every relationship as one of:

- `verified`: supported by direct code, schema, sample data, or authoritative design evidence;
- `probable`: supported by multiple consistent sources but not yet sampled;
- `unverified`: a navigation hint only and not safe for a final business conclusion.

Record source IDs for every verified map entry. Conflicting sources go to the quality report; do not silently choose the most convenient version.

## Retrieval design

When the project includes databases, business APIs, logs, code, or a reusable retrieval layer, read [data-and-rag-routing.md](data-and-rag-routing.md) and produce its routing, permission, and evaluation artifacts. Treat this as part of project knowledge-foundation delivery, not as an optional prompt-tuning step.

For actively changing project content, prefer exact and normalized keyword search over whole-corpus prompts. Expand business terms with the glossary, then traverse bounded relationships. Retrieve the smallest evidence set that can answer the question.

Recommended lookup order:

1. Function entry and glossary
2. Relevant Wiki section
3. Code-search and data maps
4. Bounded code/database/log evidence
5. Stop when direct evidence closes the question

## Runtime feedback

Store useful runtime findings as candidate knowledge with question, evidence, proposed change, confidence, owner, and review state. A scheduled knowledge-maintenance job may compare changed code, designs, schemas, and existing maps. Only approved candidates may update authoritative Wiki or maps.
