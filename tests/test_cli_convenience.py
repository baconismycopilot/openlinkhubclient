"""End-to-end tests for the convenience layer (fan/light/status/apply):
resolve-then-POST flows against mocked HTTP, mirroring the GET-merge-POST
pattern established by the dashboard-update tests."""

import json

import responses
from click.testing import CliRunner

from olh.cli import cli

BASE_URL = "http://127.0.0.1:27003"

# Two hubs (channel id 1 exists on both, deliberately) plus a non-hub device
# with a null GetDevice — the shape GET /api/devices/ really returns.
DEVICES_ENVELOPE = {
    "code": 200,
    "status": 0,
    "devices": {
        "HUB1SERIAL": {
            "ProductType": 0,
            "Product": "iCUE LINK System Hub",
            "Serial": "HUB1SERIAL",
            "GetDevice": {
                "serial": "HUB1SERIAL",
                "devices": {
                    "1": {
                        "channelId": 1,
                        "name": "iCUE LINK QX RGB",
                        "rpm": 603,
                        "temperature": 22.5,
                        "temperatureString": "22.5 °C",
                        "description": "Fan",
                        "profile": "Normal",
                        "rgb": "static",
                        "label": "GPU Intake 1",
                        "HasSpeed": True,
                    },
                    "2": {
                        "channelId": 2,
                        "name": "iCUE LINK QX RGB",
                        "rpm": 598,
                        "temperatureString": "22.1 °C",
                        "description": "Fan",
                        "profile": "Normal",
                        "rgb": "static",
                        "label": "GPU Intake 2",
                        "HasSpeed": True,
                    },
                    "3": {
                        "channelId": 3,
                        "name": "H150i",
                        "rpm": 1800,
                        "temperatureString": "28.0 °C",
                        "description": "Pump",
                        "profile": "Liquid",
                        "rgb": "rainbow",
                        "label": "H150i Pump",
                        "HasSpeed": True,
                    },
                },
                "userProfiles": {"Default": {}, "Gaming": {}},
            },
        },
        "HUB2SERIAL": {
            "ProductType": 0,
            "Product": "iCUE LINK System Hub",
            "Serial": "HUB2SERIAL",
            "GetDevice": {
                "serial": "HUB2SERIAL",
                "devices": {
                    "1": {
                        "channelId": 1,
                        "name": "iCUE LINK RX",
                        "rpm": 700,
                        "temperatureString": "23.0 °C",
                        "description": "Fan",
                        "profile": "Quiet",
                        "rgb": "watercolor",
                        "label": "Rear Fan",
                        "HasSpeed": True,
                    },
                },
            },
        },
        "MOUSESERIAL": {"Product": "Mouse", "Serial": "MOUSESERIAL", "GetDevice": None},
    },
}

TEMPERATURES_ENVELOPE = {
    "code": 200,
    "data": {"Quiet": {}, "Normal": {}, "Performance": {}},
}

COLOR_ENVELOPE = {
    "code": 200,
    "data": {
        "HUB1SERIAL": {
            "device": "Hub 1",
            "profiles": {"rainbow": {}, "static": {}, "watercolor": {}},
        },
        "HUB2SERIAL": {"device": "Hub 2", "profiles": {"rainbow": {}, "static": {}}},
    },
}

ACK = {"code": 200, "status": 1, "message": "Updated"}


def add_devices() -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/devices/", json=DEVICES_ENVELOPE)


# --- fan set ---


@responses.activate
def test_fan_set_label_percent_posts_manual(runner: CliRunner) -> None:
    add_devices()
    responses.add(responses.POST, f"{BASE_URL}/api/speed/manual", json=ACK)

    result = runner.invoke(cli, ["fan", "set", "GPU Intake 1", "50%"])

    assert result.exit_code == 0
    body = json.loads(responses.calls[1].request.body)
    assert body == {"deviceId": "HUB1SERIAL", "channelId": 1, "value": 50}


@responses.activate
def test_fan_set_bare_integer_is_manual_duty(runner: CliRunner) -> None:
    add_devices()
    responses.add(responses.POST, f"{BASE_URL}/api/speed/manual", json=ACK)

    result = runner.invoke(cli, ["fan", "set", "pump", "80"])

    assert result.exit_code == 0
    body = json.loads(responses.calls[1].request.body)
    assert body == {"deviceId": "HUB1SERIAL", "channelId": 3, "value": 80}


@responses.activate
def test_fan_set_profile_posts_canonical_name(runner: CliRunner) -> None:
    add_devices()
    responses.add(responses.GET, f"{BASE_URL}/api/temperatures/", json=TEMPERATURES_ENVELOPE)
    responses.add(responses.POST, f"{BASE_URL}/api/speed", json=ACK)

    result = runner.invoke(cli, ["fan", "set", "pump", "quiet"])

    assert result.exit_code == 0
    body = json.loads(responses.calls[2].request.body)
    assert body == {"deviceId": "HUB1SERIAL", "channelId": 3, "profile": "Quiet"}


@responses.activate
def test_fan_set_unknown_profile_lists_available_and_skips_post(runner: CliRunner) -> None:
    add_devices()
    responses.add(responses.GET, f"{BASE_URL}/api/temperatures/", json=TEMPERATURES_ENVELOPE)

    result = runner.invoke(cli, ["fan", "set", "pump", "turbo"])

    assert result.exit_code == 2
    assert "Performance" in result.output
    assert len(responses.calls) == 2  # devices + temperatures, no POST


@responses.activate
def test_fan_set_ambiguous_name_lists_matches(runner: CliRunner) -> None:
    add_devices()

    result = runner.invoke(cli, ["fan", "set", "intake", "50%"])

    assert result.exit_code == 2
    assert "GPU Intake 1" in result.output
    assert "GPU Intake 2" in result.output


@responses.activate
def test_fan_set_unknown_name_lists_channels(runner: CliRunner) -> None:
    add_devices()

    result = runner.invoke(cli, ["fan", "set", "nonsense", "50%"])

    assert result.exit_code == 2
    assert "H150i Pump" in result.output
    assert "Rear Fan" in result.output


@responses.activate
def test_fan_set_all_posts_minus_one_per_device(runner: CliRunner) -> None:
    add_devices()
    responses.add(responses.GET, f"{BASE_URL}/api/temperatures/", json=TEMPERATURES_ENVELOPE)
    responses.add(responses.POST, f"{BASE_URL}/api/speed", json=ACK)
    responses.add(responses.POST, f"{BASE_URL}/api/speed", json=ACK)

    result = runner.invoke(cli, ["fan", "set", "all", "performance"])

    assert result.exit_code == 0
    bodies = [json.loads(call.request.body) for call in responses.calls[2:]]
    assert bodies == [
        {"deviceId": "HUB1SERIAL", "channelId": -1, "profile": "Performance"},
        {"deviceId": "HUB2SERIAL", "channelId": -1, "profile": "Performance"},
    ]


@responses.activate
def test_fan_set_literal_channel_id(runner: CliRunner) -> None:
    add_devices()
    responses.add(responses.POST, f"{BASE_URL}/api/speed/manual", json=ACK)

    result = runner.invoke(cli, ["fan", "set", "3", "40%"])

    assert result.exit_code == 0
    body = json.loads(responses.calls[1].request.body)
    assert body["channelId"] == 3


# --- fan list / status ---


@responses.activate
def test_fan_list_table(runner: CliRunner) -> None:
    add_devices()

    result = runner.invoke(cli, ["fan", "list"])

    assert result.exit_code == 0
    assert "H150i Pump" in result.output
    assert "1800" in result.output


@responses.activate
def test_fan_list_json_emits_synthesized_rows(runner: CliRunner) -> None:
    add_devices()

    result = runner.invoke(cli, ["-j", "fan", "list"])

    assert result.exit_code == 0
    assert "label" in result.output
    assert "GetDevice" not in result.output


@responses.activate
def test_status_renders_dashboard_table(runner: CliRunner) -> None:
    add_devices()

    result = runner.invoke(cli, ["status"])

    assert result.exit_code == 0
    for expected in ["GPU Intake 1", "1800", "28.0", "rainbow", "Rear Fan"]:
        assert expected in result.output


# --- light ---


@responses.activate
def test_light_set_one_arg_applies_all(runner: CliRunner) -> None:
    add_devices()
    responses.add(responses.GET, f"{BASE_URL}/api/color/", json=COLOR_ENVELOPE)
    responses.add(responses.POST, f"{BASE_URL}/api/color", json=ACK)
    responses.add(responses.POST, f"{BASE_URL}/api/color", json=ACK)

    result = runner.invoke(cli, ["light", "set", "rainbow"])

    assert result.exit_code == 0
    bodies = [json.loads(call.request.body) for call in responses.calls[2:]]
    assert bodies == [
        {"deviceId": "HUB1SERIAL", "channelId": -1, "profile": "rainbow"},
        {"deviceId": "HUB2SERIAL", "channelId": -1, "profile": "rainbow"},
    ]


@responses.activate
def test_light_set_named_channel(runner: CliRunner) -> None:
    add_devices()
    responses.add(responses.GET, f"{BASE_URL}/api/color/", json=COLOR_ENVELOPE)
    responses.add(responses.POST, f"{BASE_URL}/api/color", json=ACK)

    result = runner.invoke(cli, ["light", "set", "pump", "static"])

    assert result.exit_code == 0
    body = json.loads(responses.calls[2].request.body)
    assert body == {"deviceId": "HUB1SERIAL", "channelId": 3, "profile": "static"}


@responses.activate
def test_light_set_invalid_profile_lists_available(runner: CliRunner) -> None:
    add_devices()
    responses.add(responses.GET, f"{BASE_URL}/api/color/", json=COLOR_ENVELOPE)

    result = runner.invoke(cli, ["light", "set", "pump", "disco"])

    assert result.exit_code == 2
    assert "watercolor" in result.output
    assert len(responses.calls) == 2  # no POST happened


@responses.activate
def test_light_profiles_lists_names(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/color/", json=COLOR_ENVELOPE)

    result = runner.invoke(cli, ["light", "profiles"])

    assert result.exit_code == 0
    assert "watercolor" in result.output


@responses.activate
def test_light_brightness_posts_gradual_per_device(runner: CliRunner) -> None:
    add_devices()
    responses.add(responses.POST, f"{BASE_URL}/api/brightness/gradual", json=ACK)
    responses.add(responses.POST, f"{BASE_URL}/api/brightness/gradual", json=ACK)

    result = runner.invoke(cli, ["light", "brightness", "40"])

    assert result.exit_code == 0
    bodies = [json.loads(call.request.body) for call in responses.calls[1:]]
    assert bodies == [
        {"deviceId": "HUB1SERIAL", "brightness": 40},
        {"deviceId": "HUB2SERIAL", "brightness": 40},
    ]


@responses.activate
def test_light_brightness_device_option_targets_one(runner: CliRunner) -> None:
    responses.add(responses.POST, f"{BASE_URL}/api/brightness/gradual", json=ACK)

    result = runner.invoke(cli, ["light", "brightness", "40", "-d", "HUB2SERIAL"])

    assert result.exit_code == 0
    body = json.loads(responses.calls[0].request.body)
    assert body == {"deviceId": "HUB2SERIAL", "brightness": 40}


# --- apply ---


@responses.activate
def test_apply_auto_resolves_single_profile_device(runner: CliRunner) -> None:
    add_devices()
    responses.add(responses.POST, f"{BASE_URL}/api/userProfile/change", json=ACK)

    result = runner.invoke(cli, ["apply", "gaming"])

    assert result.exit_code == 0
    body = json.loads(responses.calls[1].request.body)
    assert body == {"deviceId": "HUB1SERIAL", "userProfileName": "Gaming"}


@responses.activate
def test_apply_multiple_candidates_requires_device_id(runner: CliRunner) -> None:
    envelope = json.loads(json.dumps(DEVICES_ENVELOPE))
    envelope["devices"]["HUB2SERIAL"]["GetDevice"]["userProfiles"] = {"Silent": {}}
    responses.add(responses.GET, f"{BASE_URL}/api/devices/", json=envelope)

    result = runner.invoke(cli, ["apply", "Default"])

    assert result.exit_code == 2
    assert "HUB1SERIAL" in result.output
    assert "HUB2SERIAL" in result.output


@responses.activate
def test_apply_unknown_profile_lists_available(runner: CliRunner) -> None:
    add_devices()

    result = runner.invoke(cli, ["apply", "nonexistent"])

    assert result.exit_code == 2
    assert "Default" in result.output
    assert "Gaming" in result.output
