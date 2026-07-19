from click.testing import CliRunner

from olh.cli import cli


def test_help_shows_full_command_descriptions_untruncated(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    # Click wraps long descriptions across multiple lines; collapse
    # whitespace so a sentence spanning a line break can still be matched.
    normalized = " ".join(result.output.split())

    assert result.exit_code == 0
    # "profile"'s description has no literal "..." in it, so its presence in
    # full proves it wasn't cut short by Click's default short-help limit.
    assert "misc-device (MM700/ST100) colors." in normalized
    # "hub"'s description legitimately ends in a literal "..." as part of its
    # text; it must appear whole, not with Click's own truncation appended.
    assert "external hub ports (Link Hub, Commander Pro, ...)." in normalized
