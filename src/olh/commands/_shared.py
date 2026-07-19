"""Small helpers shared across command modules: a JSON-string click type for
nested payload fields (stages, colorZones, points, ...), a reusable
--yes/-y confirmation flag, and an RGB triplet option group."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import click


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
