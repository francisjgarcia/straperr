# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Codex, and others)
when working with code in this repository.

## What this project is

A single Flask webhook receiver (`src/main.py`) that Sonarr/Radarr ("*arr"
apps) call on their "Connect" notifications. It reacts to four event types
(`Test`, `Grab`, `Download`, `ManualInteractionRequired`) and does two
unrelated things depending on the event:

- **Grab**: logs into the private tracker HD-Olimpo and clicks "Agradecer"
  (thanks) on the matching torrent, to keep ratio/community standing.
- **ManualInteractionRequired**: calls the *arr instance's REST API to fetch
  manual-import candidates, resolve languages, POST the import, then clean
  the item out of the download queue.

There is no database, no persistent state, no auth on the webhook endpoint
itself — it's a thin bridge process meant to sit behind Sonarr/Radarr's
internal network.

## Commands

Local dev runs entirely through Docker (Chromium/chromedriver are not
expected to be present on the host):

```bash
cd docker
cp .env.example .env         # first time only
docker compose up -d --build
```

This runs the same `Dockerfile` and `gunicorn` `CMD` as production — there is
only one Dockerfile. `docker/compose.yml` passes the build arg
`INSTALL_DEV_TOOLS: "true"` so `pytest`/`flake8` get installed too (default
`false`, i.e. not present in the production image). `../src` and `../tests`
are bind-mounted into `/app`, so host edits are picked up — but gunicorn
loads the app once at boot, so a code change needs
`docker compose restart straperr` (no rebuild needed unless `docker/Dockerfile`
or `src/requirements.txt` changed).

Run a smoke-test script against a running instance (these are plain scripts
with `if __name__ == "__main__"`, not pytest test functions — despite living
in `tests/` and being pytest-invoked in CI, there is nothing for pytest to
collect here; running them directly is the actual way to exercise a code path):

```bash
docker exec straperr sh -c "cd /app/tests && python test_local_grab.py"
```

Available scripts: `test_local_connection.py` (Test event),
`test_local_download.py` (Download event), `test_local_grab.py` (Grab event —
this one hits the real hd-olimpo.club login, see below), and
`test_local_manual_interaction.py` (ManualInteractionRequired, with a full
realistic Sonarr payload). They all POST to `http://localhost:5000/`
(hardcoded in `tests/common.py`).

Lint (CI runs flake8 via an external reusable workflow with unknown exact
flags; `--max-line-length=100` passes cleanly, plain default `flake8` (79)
does not — the codebase's box-drawing comment banners alone exceed 79):

```bash
docker exec straperr sh -c "cd /app && flake8 main.py --max-line-length=100"
```

Production image build (rarely needed locally — CI builds and pushes on
every push to `main`):

```bash
docker compose -f docker/compose.yml build straperr
```

## Architecture notes that aren't obvious from one file

**Why Selenium + local Chromium, not `requests`.** hd-olimpo.club's login
form is protected by an anti-bot check that returns a "Captcha error" message
that has nothing to do with an actual solvable captcha — it's a
browser-fingerprint check. Confirmed by: the site's entire JS bundle
(`app.js`, ~550KB) has zero references to "captcha" (so nothing client-side
computes or transforms the `_captcha` hidden field), and adding artificial
delay before submit didn't change the outcome either. A plain HTTP client
cannot pass this; only a real (or real-enough headless) browser can. This is
why `hdolimpo_thanks()` in `main.py` drives actual Chromium via Selenium
instead of `requests` + BeautifulSoup — a pure-HTTP rewrite was tried and
reliably failed for this reason alone, not because of a parsing bug.

**Why Chromium is installed in the *same* container, not a separate one.**
The project used to depend on a second `selenium/standalone-chrome` container
(`straperr-selenium`, connected to via `webdriver.Remote(...)`). That's gone
— `docker/Dockerfile` now installs Alpine's `chromium`
+ `chromium-chromedriver` packages directly, and `build_chrome_driver()` in
`main.py` launches a local headless instance per call
(`CHROME_BIN`/`CHROMEDRIVER_PATH` env vars, defaulted to Alpine's install
paths). Consequence: the container needs meaningfully more memory than a
plain API service — `docker/compose.yml` reserves 300M/limits 700M. The
production-side equivalent (`DOCKER_MEMORY_LIMIT` / `DOCKER_MEMORY_RESERVATION`
GitHub Actions repo variables) lives outside this repo (see below) and needs
the same headroom.

**Chrome subprocess cleanup relies on gunicorn being PID 1.** Every
`hdolimpo_thanks()` call spawns a full Chromium process tree and tears it
down with `driver.quit()`, but subprocesses that get orphaned during
teardown (crashpad handler, renderer, GPU, zygote) reparent to PID 1. Verified
empirically that gunicorn's arbiter reaps them fine on its own (wildcard
`waitpid(-1, ...)` in its `SIGCHLD` handler) — no zombies accumulate. If PID 1
ever changes to something that doesn't reap arbitrary children (a plain shell,
for instance), zombie Chrome processes will pile up on every Grab event; add
`init: true` in compose (Docker's built-in `tini`) if that happens.

**`instanceName` means two different things depending on event type.** For
`Grab`/`Test`/`Download`, it's just a free-text label used as the logger
name (Sonarr/Radarr send whatever they're configured with, e.g.
`"TestInstance"` in the test scripts). For `ManualInteractionRequired`, it
*must* match a key in `ARR_INSTANCES` exactly (`"Sonarr"`, `"Sonarr 4K"`,
`"Radarr"`, `"Radarr 4K"`) because it's used to resolve the *arr API URL/key
— `get_arr_instance()` raises if it doesn't match. This isn't a bug, just an
overload worth knowing before "fixing" one path in terms of the other.

**HD-Olimpo page selectors are hardcoded and fragile.** The XPath/CSS
selectors in `hdolimpo_thanks()` (`@placeholder='Título'`, button text
`'Agradecer'`, `#torrent-list-table`) are coupled to hd-olimpo.club's current
markup. If thanking silently stops working, check those selectors against
the live site before assuming a logic bug.

**Deployment logic lives in a separate repo.** `.github/workflows/cicd.yml`
and `deploy.yml` are thin wrappers around reusable workflows in
`francisjgarcia/actions-templates` (`wf-build.yml`, `wf-tests.yml`,
`wf-deploy.yml`, etc.) — the actual `docker run`/container-creation flags,
and the exact flake8/pytest invocation, are defined there, not in this repo.
When something CI-related doesn't match what's in this repo's workflow
files, the answer is probably in that other repo, not here.

## Environment variables

Two separate `.env` files, both required for local Docker dev (`docker/.env`
for compose/runtime config, `src/.env` for the app itself — see
`.env.example` next to each). Full descriptions: [docs/VARIABLES.md](docs/VARIABLES.md)
(non-secret) and [docs/SECRETS.md](docs/SECRETS.md) (GitHub Actions secrets
for CI/deploy). Don't duplicate those tables here — update them instead if
variables change.
