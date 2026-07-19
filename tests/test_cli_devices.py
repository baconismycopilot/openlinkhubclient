import responses
from click.testing import CliRunner

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
