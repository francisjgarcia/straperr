---
description: Commit the current changes with a Conventional Commits message in English
---

Commit the pending changes in this repository.

Steps:
1. Run `git status` and `git diff` (staged and unstaged) to see everything that would be committed. Never use `git add -A` or `git add .` — stage specific files by name so nothing unintended (secrets, stray local files) gets swept in.
2. If there is nothing to commit, say so and stop — do not create an empty commit.
3. Decide yourself how many commits this needs and which files go in each — don't default to one giant commit just because everything is uncommitted at once. Group by logical concern: if unrelated things were touched (e.g. a CI fix and an unrelated source fix, or a docs update alongside a bug fix), split them into separate commits so each one tells a single story. Only ask the user if it's genuinely ambiguous which concern a file belongs to.
4. Write each commit message in **English**, following Conventional Commits: `<type>[optional scope]: <description>`.
   - Allowed types: `feat|fix|docs|chore|refactor|perf|test|ci|style|build` (this repo's `pr-validation` workflow enforces this same set on PR titles, max 100 characters for the description).
   - Lead with why the change matters, not a restatement of the diff.
5. Do not push. This command only commits.
6. Never use `--no-verify` or `--amend` unless the user explicitly asks.

End with a one-line summary of what was committed — list each commit made (or say there was nothing to do).
