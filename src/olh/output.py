"""Rendering helpers shared by every command: rich tables/panels by default,
raw JSON or YAML when the global --json/--yaml flag is set."""

from __future__ import annotations

import json
from typing import Any, Literal

import click
import yaml
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

console = Console()
error_console = Console(stderr=True)

OutputFormat = Literal["table", "json", "yaml"]


def render(response: Any, *, output_format: OutputFormat = "table", key: str | None = None) -> None:
    """Render an API response envelope.

    `key` names the field inside the envelope that holds the actual payload
    (e.g. "data", "device", "devices", "dashboard"); if omitted, or the key
    isn't present, the whole response is rendered.
    """
    if output_format == "json":
        print_json(response)
        return
    if output_format == "yaml":
        print_yaml(response)
        return

    payload = response
    if key is not None and isinstance(response, dict) and key in response:
        payload = response[key]

    _render_value(payload)


def _render_value(payload: Any) -> None:
    if isinstance(payload, dict):
        if not payload:
            console.print("[dim]No data returned.[/dim]")
        elif all(isinstance(v, dict) for v in payload.values()):
            print_table(_dict_of_dicts_to_rows(payload))
        else:
            print_kv(payload)
    elif isinstance(payload, list):
        if not payload:
            console.print("[dim]No data returned.[/dim]")
        elif all(isinstance(item, dict) for item in payload):
            print_table(payload)
        else:
            for item in payload:
                console.print(str(item))
    elif payload is None:
        console.print("[dim]No data returned.[/dim]")
    else:
        console.print(str(payload))


def _dict_of_dicts_to_rows(mapping: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row_key, value in mapping.items():
        row = {"id": row_key, **value}
        rows.append(row)
    return rows


def print_json(data: Any) -> None:
    console.print_json(json.dumps(data))


def print_yaml(data: Any) -> None:
    text = yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True)
    console.print(Syntax(text, "yaml", background_color="default", word_wrap=True))


_SCALAR_COLUMN_MAX = 24
_NESTED_COLUMN_MAX = 50


def print_table(rows: list[dict[str, Any]], title: str | None = None) -> None:
    if not rows:
        console.print("[dim]No results.[/dim]")
        return

    columns = list(dict.fromkeys(key for row in rows for key in row))
    table = Table(title=title, show_lines=True)
    for column in columns:
        # Cap every column's width so one unbreakable scalar (a 40-char
        # serial/id) or one big nested blob can't force Rich's shrink pass to
        # crush *other* columns down to unreadable single characters — see
        # SCALAR_COLUMN_MAX / NESTED_COLUMN_MAX below.
        has_nested = any(isinstance(row.get(column), dict | list) for row in rows)
        cap = _NESTED_COLUMN_MAX if has_nested else _SCALAR_COLUMN_MAX
        table.add_column(column, overflow="fold", max_width=cap)
    for row in rows:
        table.add_row(*(_cell(row.get(column)) for column in columns))
    console.print(table)


def print_kv(data: dict[str, Any], title: str | None = None) -> None:
    table = Table(title=title, show_header=False, box=None, show_lines=True)
    table.add_column("Field", style="bold")
    table.add_column("Value", overflow="fold")
    for field, value in data.items():
        if isinstance(value, dict):
            for sub_field, sub_value in value.items():
                table.add_row(f"{field}.{sub_field}", _cell(sub_value))
        else:
            table.add_row(field, _cell(value))
    console.print(table)


def print_ack(response: Any) -> None:
    if not isinstance(response, dict):
        console.print(str(response))
        return
    code = response.get("code")
    # The live server reports many failures as code 200 with status 0 (e.g.
    # "non-existing speed profile"), which the client doesn't raise on — only
    # a status-1 envelope is an actual success.
    ok = isinstance(code, int) and code < 400 and response.get("status") != 0
    style = "green" if ok else "red"
    message = response.get("message") or response.get("data") or ("OK" if ok else "Failed")
    console.print(f"[{style}]{message}[/{style}] (code={code})")


def confirm_or_abort(message: str, *, yes: bool) -> None:
    if yes:
        return
    if not click.confirm(message, default=False):
        raise click.Abort()


def _cell(value: Any) -> str:
    """Render a table/kv cell. Nested dict/list values are rendered as
    indented YAML blocks (no braces/quotes/commas to fight through) rather
    than summarized — the full payload stays visible in the table itself.
    Combined with fold-wrapping columns and per-row line separators, deeply
    nested API objects (e.g. a device's full GetDevice payload) grow the row
    taller instead of the column wider, which is what made early versions of
    this table unreadable."""
    if value is None:
        return ""
    if isinstance(value, dict | list):
        if not value:
            return "{}" if isinstance(value, dict) else "[]"
        text = yaml.safe_dump(value, sort_keys=False, default_flow_style=False, allow_unicode=True)
        return text.rstrip("\n")
    return str(value)
