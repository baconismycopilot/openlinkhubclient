# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`olh` is a command-line client for [OpenLinkHub](https://github.com/jurkovic-nikola/OpenLinkHub)'s REST API — a Linux daemon that controls Corsair iCUE LINK hardware (AIOs, fans, hubs, keyboards, mice, headsets) and normally exposes a web UI on `127.0.0.1:27003`. This project wraps that same HTTP API in a scriptable CLI so hardware can be controlled from the terminal instead of only the browser. It was built and verified against a real running OpenLinkHub instance (an iCUE LINK System Hub with an AIO and several fans), not just against the API docs — see "Verified against real hardware" below for what that caught.

The CLI covers the entire documented API surface (`api/README.md` in the upstream repo, fetched live from GitHub during development — there's no local copy of it in this repo, so if the upstream API changes, re-fetch that file rather than trusting this doc's endpoint list to stay current): devices, sensors, color, LED, speed, temperature profiles, macros, dashboard settings, input key reference data, keyboard/mouse/headset device settings, LCD, brightness, hub ports, ARGB, PSU, the RGB scheduler, and user/keyboard profiles. One `click.Group` per resource area, 20 groups, 70 subcommands total — plus a convenience layer (`fan`, `light`, `status`, `apply`, see "Convenience layer" under Architecture) that resolves human-friendly channel names so everyday operations don't need raw device/channel ids.

## Setup

This project is managed with [uv](https://docs.astral.sh/uv/) — use `uv`, not a manually-created venv or bare `pip`. Dependencies (`click`, `requests`, `rich`, `pyyaml`) are declared in `pyproject.toml`; add new ones with `uv add <package>` rather than editing the venv directly.

```bash
uv sync
```

`[project.scripts]` points the `olh` console-script entry point at `olh.cli:main`, so it can be installed standalone:

```bash
uv tool install --editable .
```

`--editable` means the installed `olh` command always reflects the current checkout — no reinstall needed after editing source. It lands in `~/.local/bin` (on `PATH` via `uv tool install`) and works from any directory. New dependencies still require `uv tool upgrade --reinstall olh` (the tool's env is resolved at install time, separate from this repo's `.venv`).

## Running

```bash
uv run olh --help                       # list all ~20 resource groups
uv run olh devices list                 # rich table (default)
uv run olh -j devices list              # raw API JSON (for jq/scripting)
uv run olh -y devices list              # raw API YAML
uv run olh sensors cpu                  # "45.2 °C"
uv run olh sensors cpu --clean          # 45.25
uv run olh status                       # dashboard table: every channel's profile/RPM/temp/RGB
uv run olh fan set pump quiet           # convenience layer: no ids needed (see Architecture)
uv run olh light set rainbow            # RGB effect on every channel of every device
uv run olh color set --device-id <id> --channel-id -1 --profile rainbow
uv run olh macro delete 3               # prompts "Delete macro 3 entirely? [y/N]:"
uv run olh macro delete 3 --yes         # skips the prompt
uv run olh --base-url http://192.168.1.50:27003 devices list   # a LAN instance
```

`--base-url` defaults to `http://127.0.0.1:27003` and is also settable via the `OPENLINKHUB_URL` env var, for controlling a non-local instance.

`-j/--json` and `-y/--yaml` are mutually exclusive global output modes; passing both is a `click.UsageError`, not a silently-resolved priority order.

Once installed as a tool (see Setup), drop the `uv run` prefix and call `olh` directly from anywhere.

## Linting

```bash
uv run ruff check .
uv run ruff format .
```

Both are wired into `make lint` / `make format`. `[tool.ruff]` in `pyproject.toml` selects a broad rule set (`E, F, W, I, UP, B, C4, SIM, N, RUF`) at `line-length = 100`, `target-version = "py312"` — PEP 695 generic syntax (`def f[T](...)`, used in `commands/_shared.py`'s decorators) and `X | None` unions are used freely since 3.12 is the floor.

## Architecture

```
src/olh/
├── client.py     — OpenLinkHubClient: requests.Session wrapper, error types
├── context.py    — CliContext: (client, output_format) passed to every command via @click.pass_obj
├── output.py     — all rendering: render()/print_table()/print_kv()/print_json()/print_yaml()/print_ack()/confirm_or_abort()
├── cli.py        — root click.Group (_FullHelpGroup) + global options + main() entry point
└── commands/     — one module per API resource area, each a click.Group
```

**`client.py`** wraps a `requests.Session`. `get/post/put/delete(path, json=...)` return parsed JSON. Two error types, both subclasses of `OpenLinkHubError`: `ConnectionError` (can't reach the server / timeout) and `APIError` (server responded with HTTP >= 400, *or* a 200 response whose JSON envelope has `"code" >= 400` — OpenLinkHub sometimes reports API-level errors that way rather than via the HTTP status).

**`cli.py`**'s `main()` — the actual `olh` console-script target — wraps the bare `cli()` call in `try/except OpenLinkHubError`, so a connection refusal or API error prints one clean line to stderr and exits 1, instead of a traceback. `cli()` itself (built with `cls=_FullHelpGroup`, still a `click.Group` for everything CliRunner cares about) is what tests invoke directly via `CliRunner`, so tests see the real exception object in `result.exception` rather than the swallowed/printed version.

`cli()`'s root group uses `_FullHelpGroup` instead of plain `click.Group` so plain `olh --help` shows every resource group's full one-line description. Click's default `Group.format_commands` truncates each subcommand's summary to fit on one line (`get_short_help_str(limit=...)`, ellipsis and all) before it ever reaches the word-wrapping formatter — with ~20 resource groups and several longer one-liners, real descriptions were getting cut off (see "Verified against real hardware"). `_FullHelpGroup` just passes an effectively-unlimited limit through, so `HelpFormatter.write_dl` wraps the full text across lines instead of Click truncating it first. Only the root group needs this override; no individual resource group's own `--help` (e.g. `olh temperatures --help`) has a long enough docstring to hit the default limit.

**`output.py`** is the one place response-shape decisions get made, so individual commands stay one-liners: `obj.render(response, key="data")`. `render()` extracts `response[key]` (when present) and routes by shape — dict-of-dicts → table (each sub-dict's key injected as an `id` column), list-of-dicts → table, single dict → a two-column key/value table (nested dicts flattened one level as `field.subfield` rows), scalar → printed directly, empty dict/list → `"No data returned."` rather than silent blank output (see "Verified against real hardware" — this one was a real bug, not a hypothetical). `-j/--json`/`-y/--yaml` (global flags, resolved to `CliContext.output_format`, one of `"table"`/`"json"`/`"yaml"`) bypass all of that and pretty-print the raw envelope in the requested format.

Nested dict/list *values* inside cells (e.g. a device's full `GetDevice` payload) are rendered as indented **YAML** blocks (`_cell()`, via `yaml.safe_dump`) rather than summarized — YAML's block style has no braces/quotes/commas to fight through, so it stays readable even wrapped mid-structure, which made it a better fit here than JSON once `pyyaml` was already a dependency for `-y/--yaml`. Rows grow taller instead of columns growing wider: `print_table()`/`print_kv()` set `show_lines=True` (so multi-line cells stay visually separated per row) and `overflow="fold"` per column (fold-wrap instead of Rich's default ellipsis-truncate). `print_table()` additionally caps every column's `max_width` (`_SCALAR_COLUMN_MAX` / `_NESTED_COLUMN_MAX`) so one unbroken 40-char serial/id string can't dominate Rich's shrink-widest-column-first pass and starve the nested-YAML column down to nothing — full nested detail is visible in the table itself now, not gated behind `-j`/`-y`, though those remain the better choice for scripting or genuinely narrow terminals (see "Verified against real hardware" for what changed here and why).

**Destructive commands** (`macro delete`, `macro delete-value`, `temperatures delete`, `keyboard delete-profile`, `keyboard set-layout`) share `output.confirm_or_abort(message, yes=...)` via `commands/_shared.py`'s `yes_option` decorator (adds `-y/--yes`). Declining raises `click.Abort`, which `CliRunner`/Click itself turns into a clean non-zero exit — no custom exit-code plumbing needed.

**Nested/nontrivial payload fields** (temperature graph `points`, mouse `stages`/`colorZones`) go through `commands/_shared.py`'s `JSON` click param type — a `--points '[{"x":0,"y":25},...]'`-style raw-JSON string option — rather than inventing bespoke flag-per-field syntax for arbitrarily-shaped nested data. Simple nested objects with a fixed shape (an RGB triplet) instead get typed `--red/--green/--blue` int options via the `rgb_options` decorator, since that's friendlier than requiring `--color '{"red":255,...}'` for something this common.

### Convenience layer

`fan`, `light`, `status`, and `apply` (in `commands/fan.py`, `light.py`, `status.py`, `apply.py`) sit on top of the raw 1:1 groups and mirror how the WebUI simplifies things: address channels by their user-assigned `label`, class (`pump` — which also matches description `"AIO"`, since a real AIO's pump channel reports `"AIO"` not `"Pump"`), literal channel id, or `all` (the `channelId: -1` sentinel the WebUI itself posts, fanned out per device). All resolution lives in `commands/_resolve.py`: `fetch_channels()` flattens `GET /api/devices/` (the channel map is nested at `entry["GetDevice"]["devices"]` — one level deeper than the docs example suggests at a glance), and `resolve_channel()` matches in tiers (id → exact label → description → label substring) so an exact match always beats a substring, with ambiguity/not-found raising `click.UsageError` listing the candidates. `fan set NAME VALUE` auto-detects VALUE: numeric (`50` / `50%`) → `POST /api/speed/manual` (requires `manual: true` in the daemon's config.json, else a clean 405 error), anything else → validated case-insensitively against `GET /api/temperatures/` and posted to `/api/speed` with the server's canonical casing. `light set` validates effects per-device against `GET /api/color/` *before* posting anything, so a typo can't apply to one hub then error on the next. The list-style commands (`fan list`, `light list`, `status`, `light profiles`) render *synthesized* rows through `obj.render(rows)` — so `-j`/`-y` emit the simplified projection (scriptable: `olh -j fan list | jq '.[].rpm'`), not the raw envelope; the raw envelope stays available via `olh -j devices list`. Write acks go through `output.print_ack`, which treats the server's `code: 200, status: 0` failure envelopes (how OpenLinkHub reports e.g. a nonexistent speed profile without raising an HTTP error) as failures, not successes.

## Verified against real hardware

This client was checked against a live OpenLinkHub instance, not just its docs, and that caught three real bugs before they shipped:

1. **Table rendering under real terminal width.** `devices all`/`devices list` initially dumped nested objects (`GetDevice`, `defaultColor`, `profiles`, ...) as inline JSON in table cells. Against the real API's actual response shape (a `GetDevice` payload with 36+ fields, itself containing a `devices` map of 20+ sub-devices each with 40 fields), this wrapped into an unreadable multi-thousand-character mess. First fixed by summarizing nested cell values (`{...} (36 fields, use -j/--json for detail)`) instead of inlining them; later revisited (2026-07-18) to show full nested detail as indented YAML blocks instead of hiding it — see the `output.py` paragraph above and entry below for what that took to get right against this same live device.

   Getting *that* readable against the real hub took two more passes past the obvious "just render YAML in the cell" idea: plain `overflow="fold"` on every column made Rich's shrink-widest-column-first pass target the 40-char `serial`/`id` columns (their un-splittable single line was measured as "widest" once the nested YAML column had already been broken into short lines by its own newlines), crushing those ids to one character per line. Per-column `max_width` caps (`_SCALAR_COLUMN_MAX`/`_NESTED_COLUMN_MAX` in `output.py`) fixed it — but only verified as fixed at a realistic terminal width; at a genuinely narrow one (80 cols, e.g. this sandbox's non-tty default) ten columns simply can't all be readable regardless of algorithm, which is a real constraint of this device's actual field count, not a bug to keep chasing — `-j`/`-y` remain the answer there.

2. **Plain `olh --help` was truncating command descriptions.** Not against live API data this time — against the CLI's own `--help` output at a real terminal width. Click's default `Group.format_commands` cuts each subcommand's one-line summary short (with a trailing `...`) once it doesn't fit the terminal width; with ~20 resource groups and several genuinely long one-liners (`argb`, `hub`, `profile`, ...), real description text was silently missing from `olh --help` — the exact same "cosmetic-looking width limit that actually eats data" shape as bug #1's original nested-table-cell problem. Fixed with `_FullHelpGroup` in `cli.py` (see the `cli.py` paragraph above); one wrinkle worth noting for a future re-check — `hub`'s description legitimately ends in a literal `(Link Hub, Commander Pro, ...)`, so "does the output contain `...`" isn't a valid test for "did truncation happen"; `test_cli_help.py` instead asserts specific full sentences appear intact.

3. **`dashboard update` isn't a partial patch — it's a full replace.** The upstream API docs show `POST /api/dashboard/update` with only 6 boolean fields in the example body, which reads like a patch endpoint. Against the real server, posting just those 6 fields **reset every other dashboard setting to its zero value** — `temperatureBar` and `addDeviceToDashboard` (both `true`) flipped to `false`, and `languageCode` ("en_US") became `""`. None of those three fields are even mentioned in the upstream docs' example. `commands/dashboard.py`'s `update` command now does a real read-modify-write: GET the current full settings object, overlay only the flags the user passed, POST the merged whole object back. Verified with a live round trip (GET → update with unchanged values → GET again) showing byte-identical state before and after.

Two other doc inconsistencies found while implementing (not bugs in this client, just documented here so a future re-check of the upstream docs doesn't need to re-derive it): the API README's "Save new macro profile" and "Save device RGB profile" curl examples both post to `PUT /api/macro/new`, but the RGB example's body (`deviceId`, `startColor`, `endColor`, ...) doesn't match a macro at all — almost certainly a copy/paste error upstream. Only macro creation is implemented against that endpoint. Likewise, "Set headset Zone colors" in the docs posts to `/api/mouse/zoneColors`, not a headset-specific path — `headset.py` doesn't duplicate that command since `mouse set-zone-colors` already covers the real endpoint.

## Testing

`pytest` + [`responses`](https://github.com/getsentry/responses) (mocks `requests` at the transport level — no live server needed to run the suite) + `click.testing.CliRunner`. Given ~20 command groups mostly repeat the same thin pattern (build payload → client call → render), coverage focuses on the shared plumbing where bugs actually bite rather than one test per endpoint:

- `test_client.py` — full coverage of `get/post/put/delete`, both error paths (`ConnectionError`/`Timeout` → `ConnectionError`; HTTP >= 400 *and* envelope `code` >= 400 → `APIError`), empty-body handling.
- `test_output.py` — `render()`'s shape-routing (table/kv/scalar/empty), `-j/--json` and `-y/--yaml` bypass, that nested table cells show full data (no `use -j/--json for detail` placeholder), `confirm_or_abort()`'s three paths (`yes=True` skip, declined, accepted).
- `test_cli_devices.py` — representative GET-collection and GET-single, plus the global `-j`/`-y` flags end-to-end through a real command, and that passing both together is a `click.UsageError`.
- `test_cli_help.py` — `olh --help` shows full command descriptions, not Click's default truncated-with-`...` summaries (see "Verified against real hardware" #2).
- `test_cli_writes.py` — representative POST (flat payload, nested payload like keyboard RGB), PUT, DELETE-with-confirmation (declined/accepted/`--yes`-bypassed), and the `dashboard update` GET-merge-POST behavior specifically (see "Verified against real hardware" #3 — this one has real logic worth protecting with a test, unlike the thin pass-through commands).
- `test_cli_errors.py` — a connection failure and an API error both surface as clean, non-traceback failures through `cli()` (`CliRunner`) and through `main()`'s actual error-printing/`sys.exit(1)` path.
- `test_resolve.py` — pure-unit coverage of `_resolve.py`: value parsing (`50%`/bare int/profile-name fallthrough/bounds), the tier ordering (exact label beats substring, `pump`→`AIO`), ambiguity and not-found errors, and that `fetch_channels` skips non-hub devices (null `GetDevice`, no channel map).
- `test_cli_convenience.py` — the resolve-then-POST flows end-to-end against a realistic two-hub `GET /api/devices/` fixture (channel id 1 on both hubs, deliberately): asserts the *second/third* mocked call's body carries the resolved ids and canonical profile casing, `all` fans out one POST per device with `channelId: -1`, error paths make no POST, `-j fan list` emits the synthesized rows (not the raw envelope), and brightness/apply device auto-resolution.

```bash
uv run pytest
```
