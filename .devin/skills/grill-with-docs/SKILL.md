---
name: grill-with-docs
description: Relentlessly interview the user about a plan or design while building the project's domain model and recording terms/ADRs inline.
argument-hint: "[plan or design topic]"
allowed-tools:
  - read_file
  - write_to_file
  - edit
  - multi_edit
  - grep_search
  - find_by_name
  - bash
  - command_status
  - todo_list
  - skill
  - list_resources
  - read_resource
  - search_web
  - read_url_content
triggers:
  - user
subagent: false
priority: high
auto-apply:
  - "grill with docs"
  - "边问边写文档"
  - "设计评审并记录"
  - "整理领域术语"
  - "创建 CONTEXT.md"
  - "记录架构决策"
  - "创建 ADR"
  - "领域建模"
file-patterns:
  - "**/*"
  - "CONTEXT.md"
  - "CONTEXT-MAP.md"
  - "docs/adr/*.md"
excluded-patterns:
  - "**/venv/**"
  - "**/__pycache__/**"
  - "**/.git/**"
  - "**/node_modules/**"
keywords:
  - "grill-with-docs"
  - "context"
  - "adr"
  - "domain model"
  - "glossary"
  - "ubiquitous language"
---

# Grill With Docs

Run a `/grilling` session while actively building the project's domain model. Capture the agreed vocabulary and hard decisions in durable documents as you go.

This skill is **stateful**: it writes into the repo while grilling. It leaves behind a `CONTEXT.md` glossary and, only when warranted, ADRs under `docs/adr/`.

## Grilling process

1. Ask **one question at a time**. Wait for the user's answer before continuing. Do not dump multiple questions at once.
2. Walk down the **decision tree branch by branch**. Resolve dependencies between decisions before moving to the next branch.
3. For each question, provide your **recommended answer** as a concrete proposal that the user can accept, reject, or refine.
4. If a *fact* can be found by exploring the codebase or environment (read files, grep, list directories), look it up yourself instead of asking the user.
5. The actual *decisions* are the user's. Put each one to the user and wait for their answer.
6. Do **not** implement the plan or write code until the user confirms a shared understanding.

## Domain modeling during the session

- **Challenge against the glossary.** When the user uses a term that conflicts with the existing language in `CONTEXT.md`, call it out immediately: "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"
- **Sharpen fuzzy language.** When the user uses vague or overloaded terms, propose a precise canonical term: "You're saying 'account' — do you mean the Customer or the User? Those are different things."
- **Discuss concrete scenarios.** When domain relationships are being discussed, stress-test them with specific edge-case scenarios that force the user to be precise about boundaries.
- **Cross-reference with code.** When the user states how something works, check whether the code agrees. Surface contradictions: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"
- **Update `CONTEXT.md` inline.** As soon as a term is resolved, update `CONTEXT.md` right there. Do not batch updates.
- **Offer ADRs sparingly.** Only offer to create an ADR when all three are true:
  1. The decision is **hard to reverse**.
  2. It is **surprising without context**.
  3. It is the **result of a real trade-off**.

## File structure

For most repos, use a single context:

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If `CONTEXT-MAP.md` exists at the root, the repo has multiple contexts. Read `CONTEXT-MAP.md` to find where each context lives and route terms/decisions to the correct `CONTEXT.md`.

Create files **lazily**:
- If no `CONTEXT.md` exists, create one when the first term is resolved.
- If no `docs/adr/` exists, create it when the first ADR is needed.

## `CONTEXT.md` format

```md
# {Context Name}

{One or two sentence description of what this context is and why it exists.}

## Language

**Order**:
{A one or two sentence description of the term}
_Avoid_: Purchase, transaction

**Invoice**:
A request for payment sent to a customer after delivery.
_Avoid_: Bill, payment request

**Customer**:
A person or organization that places orders.
_Avoid_: Client, buyer, account
```

Rules for `CONTEXT.md`:

- **Be opinionated.** When multiple words exist for the same concept, pick the best one and list the others under `_Avoid_`.
- **Keep definitions tight.** One or two sentences max. Define what it *is*, not what it *does*.
- **Only include terms specific to this project's context.** General programming concepts (timeouts, error types, utility patterns) don't belong.
- **Group terms under subheadings** when natural clusters emerge. A flat list is fine when all terms belong to a single cohesive area.
- **`CONTEXT.md` should be totally devoid of implementation details.** It is a glossary, not a spec or scratch pad.

## ADR format

ADRs live in `docs/adr/` and use sequential numbering: `0001-slug.md`, `0002-slug.md`, etc.

### Template

```md
# {Short title of the decision}

{1-3 sentences: what's the context, what did we decide, and why.}
```

That's it. An ADR can be a single paragraph. The value is in recording *that* a decision was made and *why* — not in filling out sections.

### Optional sections

Only include these when they add genuine value:
- **Status** frontmatter: `proposed | accepted | deprecated | superseded by ADR-NNNN`
- **Considered Options** — only when rejected alternatives are worth remembering
- **Consequences** — only when non-obvious downstream effects need to be called out

### Numbering

Scan `docs/adr/` for the highest existing number and increment by one.

### What qualifies for an ADR

- Architectural shape (monorepo, event-sourcing, CQRS, etc.)
- Integration patterns between contexts
- Technology choices that carry lock-in (database, message bus, auth provider, deployment target)
- Boundary and scope decisions
- Deliberate deviations from the obvious path
- Constraints not visible in the code
- Rejected alternatives when the rejection is non-obvious

## Where this skill fits

Use at the very start of a change, when the plan is still fuzzy and the domain language isn't settled. Typical flow:

```
grill-with-docs → to-spec → to-tickets → implement → code-review
```

If the plan is already clear and you only need to pin down terminology, use `domain-modeling` instead. If you only want the interview and don't need artifacts, use `grill-me`.
