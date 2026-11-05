---
name: bug-to-rule
description: Turn a bug you just fixed into a repo-wide check so the same mistake cannot be merged again. Use after fixing a bug, when asked to "make this a lint rule", "never again", "turn our past incidents into checks", or when seeding a rules file for a project for the first time.
---

# bug-to-rule

Goal: the same class of mistake should fail a test the moment it is written, instead of relying on someone (or some model) remembering. Notes remind; rules block.

## When to write a rule

After every fix, ask: **is the root cause a way of writing code that could appear again in another file?**

- Yes (local time treated as UTC, state written to `/tmp`, a paid API called outside the module that does the accounting, tests touching production paths...) -> write a rule.
- No, it was a one-off logic error in one place -> a normal regression test is enough. Do not force a rule.
- "Added X but forgot to update Y" (a new provider without a cost entry, a new worker missing from a lookup table) -> write a **coverage check**: take the full set from its single source of truth and assert every item exists on the other side. Never hand-write the list in the test.

## How to write it

1. **Use the test runner the project already has**, one file for all rules: `tests/test_repo_rules.py` for Python, `test/repo-rules.test.mjs` for Node, or wherever the build already runs tests. No new tools, no new dependencies. Starters are in `templates/`.
2. **Every rule carries its history**: a comment with the date and what went wrong. The failure message says how to fix it (which existing helper to use).
3. **Exceptions go in an allowlist with a reason**: `{file: why it is safe}`. Never loosen the pattern to make existing code pass.
4. **Match the pattern, not the intent**: regex or AST over source files, skip comment lines, exclude tests, dependencies and generated output.
5. **Add a self-check that the scan actually saw code**: assert a few known files are in the walk and the count is sane. If the file walk breaks, every rule passes silently. (This happened: a walker that dropped files in subfolders turned four rules into no-ops.)

## Verification you must do

1. **Run the rules against the current code first.** Look at every hit: if it is a real bug, fix it with a regression test; only safe cases go in the allowlist. The first scan often finds a live bug. That is the payoff.
2. **Poison test: break each rule on purpose in a copy** and confirm it fails. Use a scratch copy (exclude dependencies, data and secrets). **Do not break files in a working tree that production runs from**; some repos go live on save.
3. Poison-test the bug fix too: revert the fix, the new regression test must fail.
4. **Wire it into something that runs automatically**: a pre-commit hook, CI, or the `test` step of the deploy script. Read the hook's trigger conditions: if it only runs the full suite when certain folders change, run the rules file on every commit (it takes under a second).
5. Never pipe a test run into `tail` or `head`: the pipeline's exit code is the last command's, so a red suite reports success. Write output to a file and branch on the test runner's own exit code, or use `set -o pipefail`.

## Seeding rules from past incidents

For a project's first rules file: go through its incident notes, postmortems or bug history and decide for each one whether it can be a static check. Write the ones that can; skip and name the ones that cannot (they need a live API or production data). Do not pad the file with rules that would not have caught a real problem.

## Report back

- Which rules were added and which incident each one prevents.
- What the first scan found, what was fixed, and **ask before changing production data** to clean up after a bug.
- Poison test results, and which automatic gate now runs the rules.
- If you edited a working tree that serves production, say what is already live and what needs a restart.
