import json

import responses
from click.testing import CliRunner

from olh.cli import cli

BASE_URL = "http://127.0.0.1:27003"


@responses.activate
def test_post_simple_payload(runner: CliRunner) -> None:
    responses.add(responses.POST, f"{BASE_URL}/api/speed/manual", json={"code": 200, "status": 1})

    result = runner.invoke(
        cli,
        ["speed", "set-manual", "--device-id", "abc", "--channel-id", "1", "--value", "50"],
    )

    assert result.exit_code == 0
    body = json.loads(responses.calls[0].request.body)
    assert body == {"deviceId": "abc", "channelId": 1, "value": 50}


@responses.activate
def test_post_nested_payload(runner: CliRunner) -> None:
    responses.add(responses.POST, f"{BASE_URL}/api/keyboard/color", json={"code": 200, "status": 1})

    result = runner.invoke(
        cli,
        [
            "keyboard",
            "set-color",
            "--device-id",
            "abc",
            "--key-id",
            "15",
            "--scope",
            "key",
            "--red",
            "255",
            "--green",
            "0",
            "--blue",
            "128",
        ],
    )

    assert result.exit_code == 0
    body = json.loads(responses.calls[0].request.body)
    assert body["color"] == {"red": 255, "green": 0, "blue": 128}
    assert body["keyOption"] == 0


@responses.activate
def test_put_request(runner: CliRunner) -> None:
    responses.add(responses.PUT, f"{BASE_URL}/api/macro/new", json={"code": 200, "status": 1})

    result = runner.invoke(cli, ["macro", "create", "--name", "MyMacro"])

    assert result.exit_code == 0
    assert responses.calls[0].request.method == "PUT"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"macroName": "MyMacro"}


@responses.activate
def test_dashboard_update_merges_with_current_settings_before_posting(
    runner: CliRunner,
) -> None:
    """The live server replaces the whole settings object per request rather than
    patching it, so this command must GET-merge-POST or it silently zeroes out
    every field the user didn't pass (confirmed against a real instance)."""
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/dashboard",
        json={
            "code": 200,
            "dashboard": {
                "showCpu": True,
                "showGpu": True,
                "temperatureBar": True,
                "languageCode": "en_US",
            },
        },
    )
    responses.add(
        responses.POST, f"{BASE_URL}/api/dashboard/update", json={"code": 200, "status": 1}
    )

    result = runner.invoke(cli, ["dashboard", "update", "--no-show-gpu"])

    assert result.exit_code == 0
    body = json.loads(responses.calls[1].request.body)
    assert body == {
        "showCpu": True,
        "showGpu": False,
        "temperatureBar": True,
        "languageCode": "en_US",
    }


def test_delete_requires_confirmation_and_can_be_declined(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["macro", "delete", "1"], input="n\n")

    assert result.exit_code != 0


@responses.activate
def test_delete_confirmed_interactively_sends_request(runner: CliRunner) -> None:
    responses.add(
        responses.DELETE, f"{BASE_URL}/api/macro/profile", json={"code": 200, "status": 1}
    )

    result = runner.invoke(cli, ["macro", "delete", "1"], input="y\n")

    assert result.exit_code == 0
    assert len(responses.calls) == 1


@responses.activate
def test_delete_with_yes_flag_skips_prompt(runner: CliRunner) -> None:
    responses.add(
        responses.DELETE, f"{BASE_URL}/api/macro/profile", json={"code": 200, "status": 1}
    )

    result = runner.invoke(cli, ["macro", "delete", "1", "--yes"])

    assert result.exit_code == 0
    assert "Delete macro" not in result.output
    assert len(responses.calls) == 1
