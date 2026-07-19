"""Name→id resolution for the convenience commands (fan/light/status/apply):
maps human-friendly channel labels ("GPU Intake 1", "pump", "all") onto the
deviceId/channelId pairs the raw API endpoints require, and validates profile
names against what the server actually has so the canonical casing is sent."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

import click

from olh.client import OpenLinkHubClient

# The all-channels sentinel the WebUI itself sends; the server accepts any
# channelId >= -1 (api docs show 0 in one example, but -1 is what overview.js
# posts and both are handled upstream).
ALL_CHANNELS = -1


@dataclass(frozen=True)
class Channel:
    device_id: str  # hub serial — what /api/speed and /api/color call deviceId
    channel_id: int
    label: str  # user-assigned, e.g. "GPU Intake 1"
    name: str  # product/model string, e.g. "iCUE LINK QX RGB"
    description: str  # device class: "Fan", "Pump", ...
    profile: str  # current speed profile
    rgb: str  # current RGB profile
    has_speed: bool
    rpm: int | None
    temperature: str | None


def iter_hub_devices(envelope: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    """Walk a GET /api/devices/ envelope and yield (deviceId, GetDevice) per
    device, skipping non-hub entries (null GetDevice). The deviceId is the
    entry's Serial, falling back to its key in the devices map."""
    devices = envelope.get("devices") if isinstance(envelope, dict) else None
    if not isinstance(devices, dict):
        return
    for serial, entry in devices.items():
        if not isinstance(entry, dict):
            continue
        get_device = entry.get("GetDevice")
        if isinstance(get_device, dict):
            yield entry.get("Serial") or serial, get_device


def iter_channel_dicts(get_device: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield each channel sub-dict from a GetDevice payload — the map is nested
    at get_device["devices"], and real entries always carry a channelId."""
    subs = get_device.get("devices")
    if not isinstance(subs, dict):
        return
    for sub in subs.values():
        if isinstance(sub, dict) and "channelId" in sub:
            yield sub


def fetch_channels(client: OpenLinkHubClient) -> list[Channel]:
    """GET /api/devices/ and flatten every hub's channel map. Non-hub devices
    (mice, dongles) have no channel map — or a null GetDevice — and are
    skipped."""
    envelope = client.get("/api/devices/")
    return [
        Channel(
            device_id=device_id,
            channel_id=sub["channelId"],
            label=str(sub.get("label") or ""),
            name=str(sub.get("name") or ""),
            description=str(sub.get("description") or ""),
            profile=str(sub.get("profile") or ""),
            rgb=str(sub.get("rgb") or ""),
            has_speed=bool(sub.get("HasSpeed", False)),
            rpm=sub.get("rpm"),
            temperature=sub.get("temperatureString"),
        )
        for device_id, get_device in iter_hub_devices(envelope)
        for sub in iter_channel_dicts(get_device)
    ]


def resolve_targets(channels: list[Channel], text: str) -> list[tuple[str, int]]:
    """Turn user text into (deviceId, channelId) pairs to post to. "all" fans
    out to every distinct device with the all-channels sentinel; anything else
    resolves to exactly one channel or raises."""
    if text.casefold() == "all":
        device_ids = dict.fromkeys(c.device_id for c in channels)
        return [(device_id, ALL_CHANNELS) for device_id in device_ids]
    channel = resolve_channel(channels, text)
    return [(channel.device_id, channel.channel_id)]


def resolve_channel(channels: list[Channel], text: str) -> Channel:
    """Match user text against channels in tiers — literal channel id, exact
    label, exact description ("pump"), label substring — so an exact "Pump"
    description match beats a label that merely contains "pump". The first
    tier with any hit decides; more than one hit there is ambiguous."""
    wanted = text.casefold()
    # A real AIO's pump channel has description "AIO", not "Pump" (verified
    # against a live iCUE LINK hub) — "pump" must find it anyway.
    wanted_descriptions = {"pump", "aio"} if wanted == "pump" else {wanted}
    tiers: list[list[Channel]] = []
    if text.lstrip("-").isdigit():
        wanted_id = int(text)
        tiers.append([c for c in channels if c.channel_id == wanted_id])
    tiers.append([c for c in channels if c.label.casefold() == wanted])
    tiers.append([c for c in channels if c.description.casefold() in wanted_descriptions])
    tiers.append([c for c in channels if wanted in c.label.casefold()])

    for tier in tiers:
        if len(tier) == 1:
            return tier[0]
        if len(tier) > 1:
            matches = "; ".join(_describe(c) for c in tier)
            raise click.UsageError(
                f"{text!r} is ambiguous — it matches: {matches}. Use a full label or a channel id."
            )

    available = sorted(
        {c.label for c in channels if c.label} | {c.description for c in channels if c.description}
    )
    raise click.UsageError(
        f"No channel matches {text!r}. Available: {', '.join(available) or 'none'}; or use 'all'."
    )


def _describe(channel: Channel) -> str:
    return (
        f"{channel.label or channel.name} "
        f"(channel {channel.channel_id}, device {channel.device_id})"
    )


def parse_speed_value(text: str) -> int | None:
    """ "50%" or bare "50" → duty-cycle int (bounds-checked); non-numeric text
    → None, meaning the caller should treat it as a speed-profile name."""
    candidate = text.strip().removesuffix("%")
    try:
        value = int(candidate)
    except ValueError:
        return None
    if not 0 <= value <= 100:
        raise click.UsageError(f"Speed must be between 0 and 100, got {value}.")
    return value


def match_canonical(name: str, names: Iterable[str], noun: str, context: str = "") -> str:
    """Case-insensitively match `name` against the server's canonical names and
    return the server's casing; unknown names raise listing what exists."""
    names = list(names)
    for key in names:
        if key.casefold() == name.casefold():
            return key
    raise click.UsageError(
        f"Unknown {noun} {name!r}{context}. Available: {', '.join(sorted(names)) or 'none'}."
    )


def resolve_speed_profile(client: OpenLinkHubClient, name: str) -> str:
    """Case-insensitively match `name` against GET /api/temperatures/ keys and
    return the canonical key — the server validates the exact name."""
    envelope = client.get("/api/temperatures/")
    profiles = envelope.get("data") if isinstance(envelope, dict) else None
    if not isinstance(profiles, dict):
        profiles = {}
    return match_canonical(name, profiles, "speed profile")


def rgb_profiles_by_device(client: OpenLinkHubClient) -> dict[str, list[str]]:
    """GET /api/color/ → {deviceId: sorted RGB profile names}. Effects differ
    per device, so validation happens against the device that gets the POST."""
    envelope = client.get("/api/color/")
    data = envelope.get("data") if isinstance(envelope, dict) else None
    result: dict[str, list[str]] = {}
    if not isinstance(data, dict):
        return result
    for device_id, info in data.items():
        profiles = info.get("profiles") if isinstance(info, dict) else None
        if isinstance(profiles, dict):
            result[device_id] = sorted(profiles)
    return result


def resolve_rgb_profile(profiles_by_device: dict[str, list[str]], device_id: str, name: str) -> str:
    """Case-insensitively match `name` against one device's RGB profiles and
    return the canonical name."""
    profiles = profiles_by_device.get(device_id, [])
    return match_canonical(name, profiles, "RGB profile", f" for device {device_id}")
