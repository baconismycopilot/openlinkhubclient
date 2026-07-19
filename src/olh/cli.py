"""Root CLI group and console-script entry point."""

from __future__ import annotations

import sys

import click

from olh.client import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, OpenLinkHubClient, OpenLinkHubError
from olh.commands import ALL_GROUPS
from olh.context import CliContext
from olh.output import error_console


class _FullHelpGroup(click.Group):
    """click.Group whose top-level `Commands:` listing shows each
    subcommand's full one-line summary. Click's default truncates it to fit
    the terminal width (with a trailing '...'), which — with ~20 resource
    groups, several of which have longer one-line docstrings — was cutting
    real descriptions off in plain `olh --help`. `write_dl` already wraps
    long text across multiple lines on its own; the truncation happens
    earlier, in `get_short_help_str`, before the text ever reaches it."""

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None or cmd.hidden:
                continue
            commands.append((subcommand, cmd))

        if commands:
            rows = [(name, cmd.get_short_help_str(limit=10_000)) for name, cmd in commands]
            with formatter.section("Commands"):
                formatter.write_dl(rows)


@click.group(cls=_FullHelpGroup)
@click.option(
    "-u",
    "--base-url",
    envvar="OPENLINKHUB_URL",
    default=DEFAULT_BASE_URL,
    show_default=True,
    help="Base URL of a running OpenLinkHub instance. Env: OPENLINKHUB_URL.",
)
@click.option(
    "-t",
    "--timeout",
    type=float,
    default=DEFAULT_TIMEOUT,
    show_default=True,
    help="HTTP request timeout in seconds.",
)
@click.option(
    "-j",
    "--json",
    "json_output",
    is_flag=True,
    help="Print raw API JSON instead of a formatted table.",
)
@click.option(
    "-y",
    "--yaml",
    "yaml_output",
    is_flag=True,
    help="Print raw API response as YAML instead of a formatted table.",
)
@click.pass_context
def cli(
    ctx: click.Context, base_url: str, timeout: float, json_output: bool, yaml_output: bool
) -> None:
    """olh: a command-line client for the OpenLinkHub REST API."""
    if json_output and yaml_output:
        raise click.UsageError("--json and --yaml are mutually exclusive; pick one.")
    output_format = "json" if json_output else "yaml" if yaml_output else "table"
    client = OpenLinkHubClient(base_url=base_url, timeout=timeout)
    ctx.obj = CliContext(client=client, output_format=output_format)


for group in ALL_GROUPS:
    cli.add_command(group)


def main() -> None:
    try:
        cli()
    except OpenLinkHubError as exc:
        error_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
