---
name: deliberate-planning
description: Break a complex, multi-step task into a verified plan before acting. Use for tasks with several requirements, unclear scope, or more than ~3 tool calls.
version: 1.0.0
author: PythonProject
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Planning, Reasoning]
    related_skills: [verify-before-answer]
---

# Deliberate planning

## 1. Pin down the target
- Write the goal in one sentence.
- List explicit requirements (from the request) and implicit ones (format, language, constraints).
- Name what "done" looks like and how you will check it.

## 2. Explore before committing
- Gather only the facts the plan depends on (read files, search, run a quick probe).
- If two approaches are plausible, note the trade-off in one line each and pick one.

## 3. Write the plan
- Use the `todo` tool when available: 3-8 concrete steps, each with an observable result.
- Put the riskiest or most uncertain step first so failures surface early.

## 4. Execute with checkpoints
- After each step, compare the result with the step's expected outcome.
- If a step fails twice the same way, stop and re-plan instead of retrying.
- Independent sub-tasks can go to `delegate_task` in parallel.

## 5. Close out
- Load the `verify-before-answer` skill and run its checklist before replying.
