import sys

import pytest
import requests
import responses
from click.testing import CliRunner

from olh.cli import cli, main
from olh.client import APIError, ConnectionError

BASE_URL = "http://127.0.0.1:27003"


@responses.activate
def test_cli_surfaces_connection_error_without_traceback(runner: CliRunner) -> None:
    responses.add(
        responses.GET, f"{BASE_URL}/api/devices/", body=requests.ConnectionError("refused")
    )

    result = runner.invoke(cli, ["devices", "list"])

    assert result.exit_code != 0
    assert isinstance(result.exception, ConnectionError)


@responses.activate
def test_cli_surfaces_api_error(runner: CliRunner) -> None:
    responses.add(
        responses.GET, f"{BASE_URL}/api/devices/nope", json={"message": "not found"}, status=404
    )

    result = runner.invoke(cli, ["devices", "get", "nope"])

    assert result.exit_code != 0
    assert isinstance(result.exception, APIError)


@responses.activate
def test_main_prints_clean_message_and_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    responses.add(
        responses.GET, f"{BASE_URL}/api/devices/", body=requests.ConnectionError("refused")
    )
    monkeypatch.setattr(sys, "argv", ["olh", "devices", "list"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "Error" in capsys.readouterr().err
