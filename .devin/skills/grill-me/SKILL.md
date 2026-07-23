---
name: grill-me
description: Relentlessly interview the user about a plan or design until a shared understanding is reached. Stateless - no files are created.
argument-hint: "[topic or plan]"
allowed-tools:
  - read_file
  - grep_search
  - find_by_name
  - bash
  - command_status
  - search_web
  - read_url_content
  - list_resources
  - read_resource
triggers:
  - user
subagent: false
priority: high
auto-apply:
  - "grill me"
  - "grill"
  - "追问我的设计"
  - "压力测试设计"
  - "挑战我的方案"
  - "帮我把方案想清楚"
  - "一起评审设计"
file-patterns:
  - "**/*"
excluded-patterns:
  - "**/venv/**"
  - "**/__pycache__/**"
  - "**/.git/**"
  - "**/node_modules/**"
keywords:
  - "grill"
  - "stress-test"
  - "design review"
  - "plan"
  - "decision"
---

# Grill Me

Run a `/grilling` session. Interview the user relentlessly about the plan, decision, or design they have provided, until every branch of the decision tree is resolved and you and the user share the same understanding.

## Process

1. Ask **one question at a time**. Wait for the user's answer before continuing. Do not dump multiple questions at once.
2. Walk down the **decision tree branch by branch**. Resolve dependencies between decisions before moving to the next branch.
3. For each question, provide your **recommended answer** as a concrete proposal that the user can accept, reject, or refine.
4. If a *fact* can be found by exploring the codebase or environment (read files, grep, list directories, run safe commands), look it up yourself instead of asking the user.
5. The actual *decisions* are the user's. Put each one to the user and wait for their answer.
6. Do **not** act on the plan, do **not** write any code, and do **not** create files until the user confirms that you have reached a shared understanding.
7. This skill is **stateless**: do not create `CONTEXT.md`, ADRs, specs, or any other artifacts.

## When to stop

Stop when the user explicitly says something like "we're aligned", "shared understanding", "that's enough", or "let's move on".
