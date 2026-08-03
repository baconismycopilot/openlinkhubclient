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

    def render(self, response: object, *, key: str | None = None, expand: bool = False) -> None:
        output.render(response, output_format=self.output_format, key=key, expand=expand)

    def ack(self, response: object) -> bool:
        """Acknowledge a write, honouring the global -j/-y flags: the raw
        envelope in json/yaml mode (so writes stay pipeable into jq, same as
        reads), a colored one-line ack otherwise. Returns whether the envelope
        reports success — see output.ack_ok for why a 200 isn't enough."""
        if self.output_format == "json":
            output.print_json(response)
        elif self.output_format == "yaml":
            output.print_yaml(response)
        else:
            return output.print_ack(response)
        return output.ack_ok(response)
