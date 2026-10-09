---
name: verify-before-answer
description: Checklist to verify a result before giving the final answer. Use for calculations, factual claims, code changes, and any answer the user will act on.
version: 1.0.0
author: PythonProject
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Verification, Reasoning]
    related_skills: [deliberate-planning]
---

# Verify before answering

Run through every item; fix what fails before replying.

1. **Requirements** — Re-read the original request. Is every part answered, in the requested format?
2. **Independent check** — Confirm the key result a second way:
   - numbers: recompute with `execute_code` (a different formula or brute force);
   - code: run it or its tests;
   - facts: one more source, or say it is unverified.
3. **Sanity** — Are magnitude, units, sign, and edge cases plausible?
4. **Trick check** — Does the question contain a trap (wording, off-by-one, inclusive/exclusive range)? Re-read it once looking only for that.
5. **Uncertainty** — If anything is still unverified, say so in one line instead of hiding it.
