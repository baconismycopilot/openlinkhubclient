# openlinkhubclient

[![CI](https://github.com/baconismycopilot/openlinkhubclient/actions/workflows/ci.yml/badge.svg)](https://github.com/baconismycopilot/openlinkhubclient/actions/workflows/ci.yml)
[![License: GPL-3.0-only](https://img.shields.io/github/license/baconismycopilot/openlinkhubclient)](LICENSE)

A command-line client for [OpenLinkHub](https://github.com/jurkovic-nikola/OpenLinkHub)'s REST API — control Corsair iCUE LINK devices (AIOs, fans, hubs, keyboards, mice, headsets) from the terminal instead of only the web UI.

Verified against a real running OpenLinkHub instance, not just the API docs: an iCUE LINK System Hub with an iCUE LINK TITAN 360 LCD AIO and iCUE LINK RX RGB fans attached. See [CLAUDE.md](CLAUDE.md#verified-against-real-hardware) for the bugs that live testing against this hardware caught.

## Install

Requires [uv](https://docs.astral.sh/uv/) and a running OpenLinkHub instance (default `http://127.0.0.1:27003`).

```bash
uv tool install --editable .
```

This installs the `olh` command to `~/.local/bin`. Alternatively, run it from a checkout without installing:

```bash
uv sync
uv run olh --help
```

## Usage

The convenience layer covers the everyday things the OpenLinkHub web UI makes easy — no
device ids or channel ids needed; channels are addressed by their label, class ("pump"),
channel number, or "all":

```bash
olh status                   # one dashboard table: every channel's profile, RPM, temp, RGB
olh fan list                 # speed-capable channels with current profile and RPM
olh fan set pump quiet       # apply a named speed profile to the AIO pump
olh fan set all performance  # ... or to every channel on every device
olh fan set "Front Intake" 50%   # fixed duty cycle (needs `manual: true` in the daemon config)
olh light set rainbow        # RGB effect on every channel
olh light set pump static    # ... or just one
olh light profiles           # what effect names your device actually supports
olh light brightness 60      # the web UI's 0-100 brightness slider
olh apply myProfile          # switch to a saved user profile
```

Profile names are matched case-insensitively against what the server reports, and typos
list what's actually available. The full API surface remains exposed 1:1 through the
resource groups:

```bash
olh --help                 # list all resource groups (devices, sensors, color, ...)
olh devices list            # rich table by default
olh -j devices list         # raw API JSON, for piping into jq
olh sensors cpu              # "45.2 °C"
olh color set --device-id <id> --channel-id -1 --profile rainbow
olh macro delete 3           # prompts for confirmation; add --yes to skip
olh --base-url http://192.168.1.50:27003 devices list   # a non-local instance
```

`--base-url` also reads from the `OPENLINKHUB_URL` environment variable.

### Drilling into complex data

Complex values are never dumped inline. List commands summarize nested structure to a
count (`{...} (44 fields)`), get commands render each complex field as its own table one
level deep, and every get command takes an optional PATH that drills further — one key
per segment, matched case-insensitively:

```bash
olh led get <serial>                        # kv summary + one table row per channel
olh led get <serial> devices                # just the channels table
olh led get <serial> devices 1              # channel 1: LED count, pump/aio/fan flags
olh led get <serial> devices 1 channels     # per-LED color table (44 rows on an AIO)
olh led get <serial> devices 1 channels 0   # one LED's red/green/blue/Hex
olh devices get <serial> userProfiles       # the settings `devices list` omits
olh color get <serial> profiles rainbow     # one RGB effect's definition
olh temperatures get Quiet points           # a temperature profile's curve points
```

A wrong segment errors with the fields actually available at that level. `-j`/`-y` emit
just the selected subtree, so drill paths compose with jq:

```bash
olh -j led get <serial> devices 1 channels | jq 'map(.Hex) | unique'
```

## Development

```bash
make install   # uv sync
make lint      # ruff check
make format    # ruff format
make test      # pytest
```

See [CLAUDE.md](CLAUDE.md) for architecture details and design decisions.

## License

GPL-3.0-only, matching [OpenLinkHub](https://github.com/jurkovic-nikola/OpenLinkHub)'s license — see [LICENSE](LICENSE).
