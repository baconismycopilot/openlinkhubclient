"""Rendering helpers shared by every command: rich tables/panels by default,
raw JSON or YAML when the global --json/--yaml flag is set."""

from __future__ import annotations

import json
from typing import Any, Literal

import click
import yaml
from rich.console import Console
from rich.markup import escape
from rich.syntax import Syntax
from rich.table import Table

console = Console()
error_console = Console(stderr=True)

OutputFormat = Literal["table", "json", "yaml"]


def render(
    response: Any,
    *,
    output_format: OutputFormat = "table",
    key: str | None = None,
    expand: bool = False,
) -> None:
    """Render an API response envelope.

    `key` names the field inside the envelope that holds the actual payload
    (e.g. "data", "device", "devices", "dashboard"); if omitted, or the key
    isn't present, the whole response is rendered. `expand` (a get command's
    --all flag) renders every deep field as its own titled sub-table below
    the kv view; without it, deep fields stay a one-line count plus a hint
    naming the PATH that shows just that table.
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

    _render_value(payload, expand=expand)


def _render_value(
    payload: Any, *, title: str | None = None, defer: bool = True, expand: bool = False
) -> None:
    """Shape-route a payload. `title` names it when it renders as a deferred
    sub-table under a kv view. `defer` is False one sub-table level down:
    there, deep values collapse to counts instead of spawning further
    sub-tables — structure is browsed one level at a time, and anything
    deeper is reached with a get command's PATH or -j/-y."""
    if isinstance(payload, dict):
        if not payload:
            console.print("[dim]No data returned.[/dim]")
        elif all(isinstance(v, dict) for v in payload.values()):
            print_table(_dict_of_dicts_to_rows(payload), title=title)
        else:
            print_kv(payload, title=title, defer=defer, expand=expand)
    elif isinstance(payload, list):
        if not payload:
            console.print("[dim]No data returned.[/dim]")
        elif all(isinstance(item, dict) for item in payload):
            print_table(payload, title=title)
        else:
            if title:
                console.print(f"[bold]{escape(title)}[/bold]")
            for item in payload:
                console.print(_cell(item))
    elif payload is None:
        console.print("[dim]No data returned.[/dim]")
    else:
        console.print(escape(str(payload)))


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
_ATOMIC_COLUMN_MAX = 44


def _atomic_width(rendered: str) -> int:
    """Display width of a cell with no whitespace to wrap at — a serial,
    device id, or hex string. Everything else scores 0: prose folds readably
    at word boundaries, and YAML blocks and count strings already contain
    whitespace, so none of them need the wider cap."""
    if not rendered or any(char.isspace() for char in rendered):
        return 0
    return len(rendered)


def print_table(rows: list[dict[str, Any]], title: str | None = None) -> None:
    if not rows:
        console.print("[dim]No results.[/dim]")
        return

    columns = list(dict.fromkeys(key for row in rows for key in row))
    cells = [[_cell(row.get(column)) for column in columns] for row in rows]

    caps: list[int] = []
    for index, column in enumerate(columns):
        # Cap every column's width so one unbreakable scalar (a 40-char
        # serial/id) can't force Rich's shrink pass to crush *other* columns
        # down to unreadable single characters. Only flat nested values earn
        # the wider cap — they render as multi-line YAML blocks; deep values
        # are short count strings and fit the scalar cap.
        if any(_is_yaml_block(row.get(column)) for row in rows):
            caps.append(_NESTED_COLUMN_MAX)
            continue
        # ...but a cap *below* an unbreakable token's own width folds it
        # mid-token in every terminal, however wide — a 32-char serial split
        # across two lines at width 220. Those columns size to their content
        # instead (still bounded, and still narrower than the nested cap, so
        # the shrink pass keeps targeting YAML first).
        atomic = min(
            max((_atomic_width(row[index]) for row in cells), default=0), _ATOMIC_COLUMN_MAX
        )
        caps.append(max(_SCALAR_COLUMN_MAX, atomic))

    # Deliberately *not* pinning these columns to their full width with
    # min_width: when a table has enough columns to overflow the terminal
    # anyway (devices list has 11, two of them 32-char ids), forcing the ids
    # whole makes Rich drop whole columns off the right edge instead. A folded
    # id is recoverable by eye; a missing field isn't. Rich's own measurement
    # can't predict that either — a GetDevice cell's YAML embeds the 32-char
    # serial, so that column's true minimum is far wider than its content
    # suggests. Wide tables stay Rich's problem to shrink; -j/-y is the answer
    # when a terminal genuinely can't fit them.
    table = Table(title=escape(title) if title else None, show_lines=True)
    for index, column in enumerate(columns):
        table.add_column(escape(str(column)), overflow="fold", max_width=caps[index])
    for row in cells:
        table.add_row(*row)
    console.print(table)


def print_kv(
    data: dict[str, Any], title: str | None = None, *, defer: bool = True, expand: bool = False
) -> None:
    """Key/value view of a single object. Flat dict values are flattened into
    `field.subfield` rows; deep dict/list values are never rendered inline.
    At the top level of a get payload (`defer`) they collapse to a count plus
    a hint naming the PATH segment that renders just that table — unless
    `expand` (the --all flag), where they get a `see table below` marker and
    render as their own titled table after the kv block. One sub-table down
    (`defer=False`) they always collapse to a count, so structure is browsed
    one level at a time."""
    table = Table(
        title=escape(title) if title else None, show_header=False, box=None, show_lines=True
    )
    table.add_column("Field", style="bold")
    table.add_column("Value", overflow="fold")
    deferred: list[tuple[str, Any]] = []
    for field, value in data.items():
        if isinstance(value, dict | list) and _is_deep(value):
            if defer and expand:
                marker = f"[dim]see '{escape(str(field))}' table below[/dim]"
                table.add_row(escape(str(field)), marker)
                deferred.append((str(field), value))
            elif defer:
                hint = f"[dim]add '{escape(str(field))}' to the command, or --all[/dim]"
                table.add_row(escape(str(field)), f"{_cell(value)} {hint}")
            else:
                table.add_row(escape(str(field)), _cell(value))
        elif isinstance(value, dict) and value:
            for sub_field, sub_value in value.items():
                table.add_row(escape(f"{field}.{sub_field}"), _cell(sub_value))
        else:
            table.add_row(escape(str(field)), _cell(value))
    console.print(table)
    for field, value in deferred:
        _render_value(value, title=field, defer=False)


def ack_ok(response: Any) -> bool:
    """Whether a write endpoint's envelope reports success.

    The live server reports many failures as code 200 with status 0 (e.g.
    "non-existing speed profile"), which the client doesn't raise on — only a
    status-1 envelope is an actual success. A non-dict response carries no
    failure signal, so it counts as one."""
    if not isinstance(response, dict):
        return True
    code = response.get("code")
    return isinstance(code, int) and code < 400 and response.get("status") != 0


def print_ack(response: Any) -> bool:
    """Print a write command's one-line acknowledgement, and report whether it
    succeeded — so a caller can gate a follow-up call (and its own exit code)
    on it instead of charging ahead after a failed write."""
    ok = ack_ok(response)
    if not isinstance(response, dict):
        console.print(escape(str(response)))
        return ok
    style = "green" if ok else "red"
    message = response.get("message") or response.get("data") or ("OK" if ok else "Failed")
    console.print(f"[{style}]{escape(str(message))}[/{style}] (code={response.get('code')})")
    return ok


def confirm_or_abort(message: str, *, yes: bool) -> None:
    if yes:
        return
    if not click.confirm(message, default=False):
        raise click.Abort()


def _cell(value: Any) -> str:
    """Render a table/kv cell, markup-escaped. Flat dict/list values (scalars
    only, e.g. a channels map) are rendered as indented YAML blocks — no
    braces/quotes/commas to fight through, and the row grows taller instead
    of the column wider. Deep values (nesting further dicts/lists) always
    collapse to a count: complex values are never rendered inline; deeper
    structure is reached with a get command's PATH args or -j/-y."""
    if value is None:
        return ""
    if isinstance(value, dict | list):
        if not value:
            return "{}" if isinstance(value, dict) else escape("[]")
        if _is_deep(value):
            count = len(value)
            if isinstance(value, dict):
                return f"{{...}} ({count} {'field' if count == 1 else 'fields'})"
            return escape(f"[...] ({count} {'item' if count == 1 else 'items'})")
        text = yaml.safe_dump(value, sort_keys=False, default_flow_style=False, allow_unicode=True)
        return escape(text.rstrip("\n"))
    return escape(str(value))


def _is_deep(value: dict[Any, Any] | list[Any]) -> bool:
    items = value.values() if isinstance(value, dict) else value
    return any(isinstance(item, dict | list) for item in items)


def _is_yaml_block(value: Any) -> bool:
    """True when _cell will render `value` as a multi-line YAML block (a
    non-empty flat dict/list) rather than a scalar or a one-line count."""
    return isinstance(value, dict | list) and bool(value) and not _is_deep(value)
