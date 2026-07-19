import pytest
import responses
from click.testing import CliRunner
from rich.console import Console

from olh import output
from olh.cli import cli

BASE_URL = "http://127.0.0.1:27003"


@responses.activate
def test_devices_list_renders_table(runner: CliRunner) -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/devices/",
        json={
            "code": 200,
            "status": 0,
            "devices": {"D62DD3": {"Product": "iCUE LINK System Hub"}},
        },
    )

    result = runner.invoke(cli, ["devices", "list"])

    assert result.exit_code == 0
    assert "D62DD3" in result.output
    assert "iCUE LINK System Hub" in result.output


_DEVICES_WITH_CHANNELS = {
    "code": 200,
    "status": 0,
    "devices": {
        "HUBSERIAL": {
            "Product": "iCUE LINK System Hub",
            "Serial": "HUBSERIAL",
            "GetDevice": {
                "Debug": False,
                "serial": "HUBSERIAL",
                "firmware": "2.11.517",
                "aio": False,
                "brightness": 3,
                "devices": {
                    "1": {"channelId": 1, "label": "GPU Intake 1", "description": "Fan"},
                    "2": {"channelId": 2, "label": "H150i Pump", "description": "AIO"},
                },
                "userProfiles": {"Default": {}, "Gaming": {}},
            },
        },
        "MOUSESERIAL": {"Product": "Mouse", "Serial": "MOUSESERIAL", "GetDevice": None},
    },
}


@responses.activate
def test_devices_list_table_shows_channels_column(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Wide console so the channels cell doesn't fold mid-string at the
    # CliRunner's default 80-column width.
    monkeypatch.setattr(output, "console", Console(force_terminal=False, width=200))
    responses.add(responses.GET, f"{BASE_URL}/api/devices/", json=_DEVICES_WITH_CHANNELS)

    result = runner.invoke(cli, ["devices", "list"])

    assert result.exit_code == 0
    assert "channels" in result.output
    assert "GPU Intake 1 (Fan)" in result.output
    assert "H150i Pump (AIO)" in result.output
    # The GetDevice cell keeps only string-valued keys; the structured/flag
    # fields are reachable via `devices get <id> [KEY]` instead.
    assert "serial: HUBSERIAL" in result.output
    assert "firmware: 2.11.517" in result.output
    for hidden in ("channelId", "Debug", "aio", "brightness", "userProfiles"):
        assert hidden not in result.output


@responses.activate
def test_devices_list_json_stays_raw_envelope(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/devices/", json=_DEVICES_WITH_CHANNELS)

    result = runner.invoke(cli, ["-j", "devices", "list"])

    assert result.exit_code == 0
    assert '"channels"' not in result.output
    assert '"channelId"' in result.output


@responses.activate
def test_devices_get_renders_single_device(runner: CliRunner) -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/devices/D62DD3",
        json={"code": 200, "status": 0, "device": {"Product": "iCUE LINK System Hub"}},
    )

    result = runner.invoke(cli, ["devices", "get", "D62DD3"])

    assert result.exit_code == 0
    assert "iCUE LINK System Hub" in result.output


_SINGLE_DEVICE = {
    "code": 200,
    "status": 0,
    "device": {
        "serial": "HUBSERIAL",
        "aio": False,
        "devices": {
            "1": {"channelId": 1, "label": "GPU Intake 1", "description": "Fan"},
        },
        "userProfiles": {"Default": {}, "Gaming": {}},
    },
}


@responses.activate
def test_devices_get_key_drills_into_field(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/devices/HUBSERIAL", json=_SINGLE_DEVICE)

    result = runner.invoke(cli, ["devices", "get", "HUBSERIAL", "devices"])

    assert result.exit_code == 0
    assert "GPU Intake 1" in result.output
    assert "userProfiles" not in result.output


@responses.activate
def test_devices_get_key_is_case_insensitive_and_json_emits_subtree(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/devices/HUBSERIAL", json=_SINGLE_DEVICE)

    result = runner.invoke(cli, ["-j", "devices", "get", "HUBSERIAL", "USERPROFILES"])

    assert result.exit_code == 0
    assert '"Gaming"' in result.output
    assert '"code"' not in result.output


@responses.activate
def test_devices_get_unknown_key_lists_available_fields(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/devices/HUBSERIAL", json=_SINGLE_DEVICE)

    result = runner.invoke(cli, ["devices", "get", "HUBSERIAL", "nope"])

    assert result.exit_code != 0
    assert "No field 'nope'" in result.output
    assert "userProfiles" in result.output


@responses.activate
def test_json_flag_prints_raw_json(runner: CliRunner) -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/devices/",
        json={"code": 200, "status": 0, "devices": {}},
    )

    result = runner.invoke(cli, ["-j", "devices", "list"])

    assert result.exit_code == 0
    assert '"code": 200' in result.output


@responses.activate
def test_yaml_flag_prints_raw_yaml(runner: CliRunner) -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/devices/",
        json={"code": 200, "status": 0, "devices": {}},
    )

    result = runner.invoke(cli, ["-y", "devices", "list"])

    assert result.exit_code == 0
    assert "code: 200" in result.output


def test_json_and_yaml_flags_are_mutually_exclusive(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["-j", "-y", "devices", "list"])

    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


@responses.activate
def test_sensors_cpu(runner: CliRunner) -> None:
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/cpuTemp",
        json={"code": 200, "status": 1, "data": "45.2 °C"},
    )

    result = runner.invoke(cli, ["sensors", "cpu"])

    assert result.exit_code == 0
    assert "45.2" in result.output
