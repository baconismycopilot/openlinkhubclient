"""Small helpers shared across command modules: a JSON-string click type for
nested payload fields (stages, colorZones, points, ...), a hex/triplet color
type, a reusable --yes/-y confirmation flag, an RGB triplet option group, and
the PATH drill-down walker used by the single-resource get commands."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

import click

from olh.context import CliContext


class JsonParamType(click.ParamType):
    name = "json"

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> Any:
        if not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            self.fail(f"{value!r} is not valid JSON: {exc}", param, ctx)


JSON = JsonParamType()


_HEX_COLOR = re.compile(r"[0-9a-fA-F]{6}")


# Named colors are deliberately not supported: the point of this type is an
# unambiguous triplet, and a half-remembered CSS name list is a worse failure
# mode than "give me six hex digits".
class ColorParamType(click.ParamType):
    """A color as `#rrggbb`, `rrggbb`, `#rgb`, or `r,g,b` -> the API's
    {"red": .., "green": .., "blue": ..} object."""

    name = "color"

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> Any:
        if isinstance(value, dict):
            return value
        text = str(value).strip()
        if "," in text:
            parts = [p.strip() for p in text.split(",")]
            if len(parts) != 3:
                self.fail(f"{value!r} needs exactly three comma-separated channels.", param, ctx)
            try:
                channels = [int(p) for p in parts]
            except ValueError:
                self.fail(f"{value!r} has a non-integer channel.", param, ctx)
            if any(c < 0 or c > 255 for c in channels):
                self.fail(f"{value!r} has a channel outside 0-255.", param, ctx)
        else:
            digits = text.removeprefix("#")
            if len(digits) == 3:
                digits = "".join(d * 2 for d in digits)
            # Validate the whole string up front rather than leaning on
            # int(..., 16) to reject the bad pairs: it also accepts signs and
            # whitespace, so '#ff-00f' parses as a perfectly plausible color
            # and the wrong one gets pushed to the hardware without a word.
            if not _HEX_COLOR.fullmatch(digits):
                self.fail(
                    f"{value!r} is not a color: use '#rrggbb', '#rgb', or 'r,g,b'.", param, ctx
                )
            channels = [int(digits[i : i + 2], 16) for i in (0, 2, 4)]
        return dict(zip(("red", "green", "blue"), channels, strict=True))


COLOR = ColorParamType()


def yes_option[F: Callable[..., Any]](f: F) -> F:
    return click.option(
        "-y", "--yes", is_flag=True, default=False, help="Skip the confirmation prompt."
    )(f)


def rgb_options[F: Callable[..., Any]](f: F) -> F:
    f = click.option("-b", "--blue", type=click.IntRange(0, 255), required=True)(f)
    f = click.option("-g", "--green", type=click.IntRange(0, 255), required=True)(f)
    f = click.option("-r", "--red", type=click.IntRange(0, 255), required=True)(f)
    return f


def path_argument[F: Callable[..., Any]](f: F) -> F:
    """The variadic PATH argument every drill-capable get command takes."""
    return click.argument("path", nargs=-1)(f)


def all_option[F: Callable[..., Any]](f: F) -> F:
    """The --all flag every drill-capable get command takes: render every
    deep field as its own sub-table below the kv view, instead of the
    default one-line count with a PATH hint."""
    return click.option(
        "--all",
        "show_all",
        is_flag=True,
        default=False,
        help="Render every nested table below the main view (default: counts with a PATH hint).",
    )(f)


def exit_if_write_failed(ok: bool) -> None:
    """Exit 1 when a write command's ack reported failure.

    Worth a helper because the failure it catches is invisible to the client:
    the server reports plenty of rejections (a nonexistent speed profile, an
    out-of-range RGB speed) as a `code: 200, status: 0` envelope rather than an
    HTTP error, so nothing raises and a fanned-out write would otherwise report
    success to `olh fan set ... && ...` after changing nothing. Commands that
    write to several channels/devices at once ack each one, then pass the
    accumulated verdict here — every write still gets attempted, exactly as
    before; only the exit code changes."""
    if not ok:
        click.get_current_context().exit(1)


def drill(payload: Any, path: tuple[str, ...]) -> Any:
    """Walk PATH segments into a payload one level at a time: dict keys by
    exact match first, then case-insensitively (the API mixes casings and
    uses numeric-string keys) — erroring if the fold is ambiguous — and list
    items by index. Complex values are never rendered inline, so this is how
    a get command reaches deeper structure."""

    def where(depth: int) -> str:
        return " -> ".join(path[:depth]) or "the payload"

    node = payload
    for depth, segment in enumerate(path):
        if isinstance(node, dict):
            if segment in node:
                node = node[segment]
                continue
            target = segment.casefold()
            matches = [k for k in node if str(k).casefold() == target]
            if not matches:
                available = ", ".join(str(k) for k in node)
                raise click.UsageError(
                    f"No field {segment!r} in {where(depth)}. Available: {available}."
                )
            if len(matches) > 1:
                candidates = ", ".join(repr(str(k)) for k in matches)
                raise click.UsageError(
                    f"{segment!r} is ambiguous in {where(depth)}: matches {candidates}."
                )
            node = node[matches[0]]
        elif isinstance(node, list):
            try:
                node = node[int(segment)]
            except (ValueError, IndexError):
                raise click.UsageError(
                    f"{where(depth)} is a list of {len(node)} items; "
                    f"{segment!r} is not a valid index."
                ) from None
        else:
            raise click.UsageError(f"{where(depth)} is {node!r}; cannot drill into {segment!r}.")
    return node


def render_subtree(
    obj: CliContext, response: Any, path: tuple[str, ...], *, key: str, expand: bool = False
) -> None:
    """Shared body of the drill-capable get commands: with no PATH, render
    the envelope's payload; with one, drill into it and render (and -j/-y
    emit) just that subtree, jq-ready. Mirrors render()'s envelope handling:
    the payload lives under `key` when present, else the whole response —
    so anything visible without a PATH is also drillable with one. `expand`
    (the --all flag) renders deep fields as sub-tables instead of counts —
    it applies to the drilled subtree too, so PATH plus --all expands one
    level below wherever the PATH landed."""
    if not path:
        obj.render(response, key=key, expand=expand)
        return
    payload = response[key] if isinstance(response, dict) and key in response else response
    obj.render(drill(payload, path), expand=expand)
