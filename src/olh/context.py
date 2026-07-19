"""Shared CLI context object passed to every command via @click.pass_obj."""

from __future__ import annotations

from dataclasses import dataclass

from olh import output
from olh.client import OpenLinkHubClient
from olh.output import OutputFormat


@dataclass
class CliContext:
    client: OpenLinkHubClient
    output_format: OutputFormat = "table"

    def render(self, response: object, *, key: str | None = None) -> None:
        output.render(response, output_format=self.output_format, key=key)
