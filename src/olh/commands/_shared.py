"""Small helpers shared across command modules: a JSON-string click type for
nested payload fields (stages, colorZones, points, ...), a reusable
--yes/-y confirmation flag, an RGB triplet option group, and the PATH
drill-down walker used by the single-resource get commands."""

from __future__ import annotations

import json
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


def render_subtree(obj: CliContext, response: Any, path: tuple[str, ...], *, key: str) -> None:
    """Shared body of the drill-capable get commands: with no PATH, render
    the envelope's payload; with one, drill into it and render (and -j/-y
    emit) just that subtree, jq-ready. Mirrors render()'s envelope handling:
    the payload lives under `key` when present, else the whole response —
    so anything visible without a PATH is also drillable with one."""
    if not path:
        obj.render(response, key=key)
        return
    payload = response[key] if isinstance(response, dict) and key in response else response
    obj.render(drill(payload, path))
