---
description: Commit any pending changes (Conventional Commits, English) and push — creating a proper branch first if currently on main
---

Push the current work to its remote in a single push.

This shares the same "current state" model as `/pr` — keep both consistent if you ever change one:

| Current state | What `/push` does |
| --- | --- |
| On `main` | Create a feature branch first (`/branch`'s logic), then push that. |
| On a feature branch, no PR open for it yet | Commit if needed, push. Nothing else — no PR gets created here. |
| On a feature branch that already has an open PR | Commit if needed, push. This lands the new commits on that same PR automatically — do **not** create a new branch just because a PR already exists. |

Steps:
1. Check the current branch. If it's `main` (or any default/protected branch), follow `/branch`'s logic to create a suitably named feature branch first (infer the name from the pending changes if not obvious), then continue the remaining steps on that new branch. Otherwise, stay on the current branch regardless of whether it already has an open PR — never create a new branch just to push more commits to an existing PR.
2. If there are uncommitted changes, commit them first following `/commit`'s rules: stage specific files (never `-A`/`.`), split unrelated changes into separate commits, write messages in English as Conventional Commits (`feat|fix|docs|chore|refactor|perf|test|ci|style|build`, max 100 char description — same set this repo's `pr-validation` workflow checks on PR titles).
3. Check for commits ahead of the remote (`git rev-list @{u}..HEAD --count`, or if there's no upstream yet, everything on the branch is unpushed).
4. If there is nothing to commit and nothing unpushed, say so and stop — do not push an empty no-op.
5. Push everything in **one** `git push` (add `-u origin <branch>` if the branch has no upstream yet) — don't push after each individual commit if `/commit` created several; one push covers all of them. Never force-push unless the user explicitly asks.

End with a one-line summary: what was committed (if anything), whether a new branch was created, and that the push succeeded, with the branch name. If the branch already has an open PR, mention its URL too (the push just updated it).
