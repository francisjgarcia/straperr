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

Local dev runs entirely through Docker:

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

**HD-Olimpo is driven over plain HTTP (`requests` + BeautifulSoup), no
browser.** hd-olimpo.club runs UNIT3D. Its login form is protected by UNIT3D's
HiddenCaptcha, which is validated entirely server-side: an encrypted `_captcha`
token (bound to session, IP and User-Agent), a CSS-hidden honeypot `_username`
that must be *present and empty*, and a randomly-named field whose value must
equal the token's timestamp. `hdolimpo_login()` passes it by GETting `/login`
and re-POSTing *every* form input verbatim within the same `requests.Session`
(same cookie + User-Agent). The project used Selenium + headless Chromium for
a while on the belief that this was a browser-fingerprint check; it isn't — a
pure-HTTP login was verified working. If a "Captcha error" ever comes back,
first check that no form field is being dropped before reaching for a browser.

**"Agradecer" is a Livewire 3 call, not a form.** The thanks button is the
`thank-button` Livewire component (`wire:click="store(<torrent id>)"`).
`hdolimpo_click_thanks()` replays what `livewire.js` does: POST JSON to the
update URI from `window.livewireScriptConfig` (currently `/livewire/update`,
with the CSRF token from the same object) carrying the component's
`wire:snapshot` and the call. The result comes back as a dispatched toast
event: `success` ("Your thank was successfully applied!") or `error` ("You
have already thanked!", or another reason). The button is picked by
`memo.name == "thank-button"` in its snapshot, not by `wire:click` —
`bookmark-button` on the same page also calls `store(<id>)`.

**`instanceName` means two different things depending on event type.** For
`Grab`/`Test`/`Download`, it's just a free-text label used as the logger
name (Sonarr/Radarr send whatever they're configured with, e.g.
`"TestInstance"` in the test scripts). For `ManualInteractionRequired`, it
*must* match a key in `ARR_INSTANCES` exactly (`"Sonarr"`, `"Sonarr 4K"`,
`"Radarr"`, `"Radarr 4K"`) because it's used to resolve the *arr API URL/key
— `get_arr_instance()` raises if it doesn't match. This isn't a bug, just an
overload worth knowing before "fixing" one path in terms of the other.

**HD-Olimpo page selectors are hardcoded and fragile.** The selectors in
the `hdolimpo_*` helpers (`form[action$="/login"]`,
`a.torrent-search--list__name` on `/torrents?name=...`, the `thank-button`
Livewire component, `window.livewireScriptConfig`) are coupled to
hd-olimpo.club's current markup. Search results are matched by *exact*
(whitespace-normalized) name, so a release title that differs from the
site's name (e.g. the site adds "(Edición 2026)") logs "Sin coincidencia
exacta" and nothing is thanked. If thanking silently stops working, check
those selectors against the live site before assuming a logic bug.

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
