---
description: Commit/push if needed, then open a GitHub PR using this repo's template, assigned to the user with the right labels
---

Open a pull request for the current branch against `main`.

This shares the same "current state" model as `/push` — keep both consistent if you ever change one:

| Current state | What `/pr` does |
| --- | --- |
| On `main` | Create a feature branch first (`/branch`'s logic), then treat it as a fresh branch with no PR (continue below). |
| On a feature branch, no PR open for it yet | Commit if needed, push, then create the PR. |
| On a feature branch that already has an open PR | Commit if needed, push (landing new commits on that PR) — then **stop and report that PR's URL**. Never create a second branch or a duplicate PR just because you ran `/pr` again. |

Steps:
1. If the current branch is `main`, follow `/branch`'s logic to create a suitably named feature branch first — never open a PR from `main` itself. Otherwise stay on the current branch.
2. Run `git status` and `git diff` to see pending changes, and check whether the branch has unpushed commits.
3. If there are uncommitted changes, commit them first following `/commit`'s rules: stage specific files by name (never `-A`/`.`), split unrelated changes into separate commits, English Conventional Commit messages.
4. Push the branch if it isn't already up to date with its remote (add `-u origin <branch>` if it has no upstream yet). Never force-push.
5. Check with `gh pr list --head <branch>` whether a PR already exists for this branch:
   - If one exists, the commit+push above already updated it — report its URL and stop here. Do not create a new branch or a second PR.
   - Otherwise, continue to create one below.
6. Review the full commit history that will go into the PR (`git log origin/main..HEAD`), not just the latest commit, to write an accurate title and body.
7. **Title** (English): Conventional Commits format — `<type>[optional scope]: <description>`, type one of `feat|fix|docs|chore|refactor|perf|test|ci|style|build`, description max 100 characters. This repo's `pr-validation` workflow (`wf-pr-validation.yml`) enforces this exact pattern and will fail the check otherwise.
8. **Body** (English): use `.github/pull_request_template.md` as the structure — don't skip sections, and don't leave every checkbox unchecked as a lazy default. For each item, actually verify it before checking it:
   - **Type of change**: check the box(es) matching the commit type(s) actually used.
   - **Checklist**: read `CONTRIBUTING.md` and `docs/STYLEGUIDE.md` if unsure, then check each item only if genuinely true for this change (e.g. don't check "tests pass" without having actually run them, don't check "documentation updated" without having checked whether any doc references the thing being changed — `grep` for the changed variable/function names across `README.md` and `docs/` first). Leave boxes unchecked (with a short inline note why) when an item doesn't apply rather than checking it dishonestly.
   - **Additional Notes**: call out anything a reviewer must do before merging (e.g. a repo variable that needs to be set) and any known limitation (e.g. tests that don't actually run in CI).
9. **Assignee**: default to `@me` (the authenticated user) unless the user says otherwise for this PR.
10. **Labels**: pick from the repo's actual labels (`gh label list`) based on what the PR does — don't invent label names. If nothing fits well, leave unlabeled rather than forcing one.
11. Create the PR:
    ```
    gh pr create --title "..." --body "$(cat <<'EOF'
    ...
    EOF
    )" --assignee @me --label <name> [--label <name> ...]
    ```
    **Known gh CLI bug in this repo**: `gh pr create`/`gh pr edit` can fail with `GraphQL: Projects (classic) is being deprecated ... (repository.pullRequest.projectCards)` even though the mutation itself (assignee/label/body) is unrelated to Projects. If that happens:
    - Retry `gh pr create` with just `--title`/`--body` (no assignee/label) to get the PR created.
    - Then set assignee/labels/body via the REST API instead of `gh pr edit`, e.g.:
      ```
      echo '{"assignees":["<login>"]}' | gh api -X POST repos/<owner>/<repo>/issues/<n>/assignees --input -
      echo '{"labels":["<label>"]}'    | gh api -X POST repos/<owner>/<repo>/issues/<n>/labels --input -
      gh api -X PATCH repos/<owner>/<repo>/pulls/<n> --input <json-file-with-body-field>
      ```
12. Report the PR URL when done.
