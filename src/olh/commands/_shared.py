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


def drill(payload: Any, path: tuple[str, ...]) -> Any:
    """Walk PATH segments into a payload one level at a time: dict keys are
    matched case-insensitively (the API mixes casings and uses numeric-string
    keys), list items by index. Complex values are never rendered inline, so
    this is how a get command reaches deeper structure."""
    node = payload
    for depth, segment in enumerate(path):
        where = " -> ".join(path[:depth]) or "the payload"
        if isinstance(node, dict):
            match = next((k for k in node if str(k).casefold() == segment.casefold()), None)
            if match is None:
                available = ", ".join(str(k) for k in node)
                raise click.UsageError(f"No field {segment!r} in {where}. Available: {available}.")
            node = node[match]
        elif isinstance(node, list):
            try:
                node = node[int(segment)]
            except (ValueError, IndexError):
                raise click.UsageError(
                    f"{where} is a list of {len(node)} items; {segment!r} is not a valid index."
                ) from None
        else:
            raise click.UsageError(f"{where} is {node!r}; cannot drill into {segment!r}.")
    return node


def render_subtree(obj: CliContext, response: Any, path: tuple[str, ...], *, key: str) -> None:
    """Shared body of the single-resource get commands: with no PATH, render
    the envelope's payload; with one, drill into it and render (and -j/-y
    emit) just that subtree, jq-ready."""
    if not path:
        obj.render(response, key=key)
        return
    payload = response.get(key) if isinstance(response, dict) else None
    if not isinstance(payload, dict | list):
        raise click.UsageError("The response has no payload to drill into.")
    obj.render(drill(payload, path))
