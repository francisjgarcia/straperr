---
description: Create a new branch off the current one and sync it with main early to avoid conflicts later
argument-hint: [branch-name]
---

Create a new branch that continues from the current branch's state, and merge the latest `main` into it right away — catching and resolving any conflicts now instead of later at PR time.

Steps:
1. Determine the branch name:
   - If `$ARGUMENTS` was given, use it as-is (assume the user chose it deliberately).
   - Otherwise infer one from the pending/recent changes: `<type>/<short-kebab-slug>`, using the same Conventional Commit types as `/commit` (`feat|fix|docs|chore|refactor|perf|test|ci|style|build`).
2. If there are uncommitted changes, stash them first with a descriptive message (`git stash push -m "..."`) so the branch switch is clean. Don't use a blanket stash if only some of the working tree changes are meant to travel with this branch — stash specific paths (`git stash push -- <paths>`) and leave the rest untouched.
3. `git fetch origin` to get the latest `main`.
4. `git checkout -b <branch-name>` from the current HEAD (not from `origin/main` — this branches off what you already have).
5. `git merge origin/main`. If there are conflicts, resolve them properly (understand both sides of each hunk — don't blindly pick one) rather than punting back to the user unless a conflict requires a decision only they can make.
6. If anything was stashed in step 2, `git stash pop` and resolve any conflicts there too.
7. Do not push — that's `/push`'s job.

End with a one-line summary: the new branch name, whether it needed conflict resolution (and what kind), and confirmation it's ready to keep working on.
