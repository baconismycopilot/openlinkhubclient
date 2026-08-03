"""Tests for editing a stored RGB profile's colors (PUT /api/color/change).

`color set` only picks which profile is active; the color itself lives in the
profile, so setting a literal color goes through `color change` / `light color`.
Like `dashboard update`, the endpoint is a full replace rather than a patch, so
the read-modify-write is the part worth protecting with a test."""

import json

import pytest
import responses
from click.testing import CliRunner

from olh.cli import cli
from olh.commands._shared import COLOR

BASE_URL = "http://127.0.0.1:27003"

# Every field the update endpoint rebuilds from the request body -- anything
# the command forgets to carry over reverts to a zero value.
PROFILES = {
    "static": {
        "speed": 4,
        "brightness": 1,
        "smoothness": 20,
        "start": {"red": 0, "green": 255, "blue": 255, "brightness": 0.5},
        "middle": {"red": 0, "green": 0, "blue": 0, "brightness": 0},
        "end": {"red": 0, "green": 255, "blue": 255, "brightness": 0.5},
        "gradients": None,
        "minTemp": 10,
        "maxTemp": 60,
        "profileName": "Static",
        "alternateColors": True,
        "rgbDirection": 1,
    },
    "off": {
        "speed": 0,
        "start": {"red": 0, "green": 0, "blue": 0},
        "middle": {"red": 0, "green": 0, "blue": 0},
        "end": {"red": 0, "green": 0, "blue": 0},
        "minTemp": 0,
        "maxTemp": 0,
        "profileName": "Off",
    },
}

DEVICE_COLOR = {"device": "iCUE LINK System Hub", "profiles": PROFILES}

# GET /api/color/ is keyed by serial; GET /api/color/<id> returns the device
# object directly. The two shapes really do differ -- verified against a live
# hub -- and the change flow reads both.
COLOR_LIST_ENVELOPE = {"code": 200, "status": 0, "data": {"HUB1SERIAL": DEVICE_COLOR}}
COLOR_ENVELOPE = {"code": 200, "status": 0, "data": DEVICE_COLOR}

# A second hub whose `static` is stored with a speed the server rejects -- the
# realistic way one device in a multi-device write fails while the first
# succeeds.
SLOW_DEVICE_COLOR = {
    "device": "iCUE LINK System Hub",
    "profiles": {"static": {**PROFILES["static"], "speed": 0}},
}
TWO_HUB_LIST_ENVELOPE = {
    "code": 200,
    "status": 0,
    "data": {"HUB1SERIAL": DEVICE_COLOR, "HUB2SERIAL": SLOW_DEVICE_COLOR},
}
SLOW_COLOR_ENVELOPE = {"code": 200, "status": 0, "data": SLOW_DEVICE_COLOR}
FAILURE_ENVELOPE = {"code": 200, "status": 0, "message": "txtInvalidSpeed"}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("#ff00ff", {"red": 255, "green": 0, "blue": 255}),
        ("ff00ff", {"red": 255, "green": 0, "blue": 255}),
        ("#f0f", {"red": 255, "green": 0, "blue": 255}),
        ("0,128,255", {"red": 0, "green": 128, "blue": 255}),
        (" 0 , 128 , 255 ", {"red": 0, "green": 128, "blue": 255}),
    ],
)
def test_color_param_accepts(text: str, expected: dict[str, int]) -> None:
    assert COLOR.convert(text, None, None) == expected


# "#ff-00f" is the one worth pinning: int(pair, 16) accepts signs and spaces,
# so before the shape check it parsed to a valid-looking (wrong) color.
@pytest.mark.parametrize(
    "text",
    ["ff00", "#gggggg", "0,128", "300,0,0", "-1,0,0", "0,x,0", "#ff-00f", "#ff 00f", "#+f0+f0"],
)
def test_color_param_rejects(text: str) -> None:
    with pytest.raises(Exception, match=r"color|channel|hex"):
        COLOR.convert(text, None, None)


@responses.activate
def test_change_is_read_modify_write(runner: CliRunner) -> None:
    """Only --start was passed, so middle/end and every non-color field must be
    carried over from the GET rather than reverting to zero values."""
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/color/change",
        json={"code": 200, "status": 1, "message": "RGB profile is successfully updated"},
    )

    result = runner.invoke(
        cli, ["color", "change", "-d", "HUB1SERIAL", "-p", "static", "-s", "#ff00ff"]
    )

    assert result.exit_code == 0, result.output
    body = json.loads(responses.calls[1].request.body)
    assert body["startColor"] == {"red": 255, "green": 0, "blue": 255}
    # Untouched colors keep their stored values, reduced to the three channels
    # the endpoint validates.
    assert body["endColor"] == {"red": 0, "green": 255, "blue": 255}
    assert body["middleColor"] == {"red": 0, "green": 0, "blue": 0}
    # Stored-name -> request-name mapping, and nothing silently zeroed.
    assert body["speed"] == 4
    assert body["rgbMinTemp"] == 10
    assert body["rgbMaxTemp"] == 60
    assert body["alternateColors"] is True
    assert body["rgbDirection"] == 1
    assert body["colorZones"] is None


@responses.activate
def test_change_matches_profile_case_insensitively(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)
    responses.add(responses.PUT, f"{BASE_URL}/api/color/change", json={"code": 200, "status": 1})

    result = runner.invoke(
        cli, ["color", "change", "-d", "HUB1SERIAL", "-p", "STATIC", "-s", "#010203"]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(responses.calls[1].request.body)["profile"] == "static"


@responses.activate
def test_change_unknown_profile_makes_no_put(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)

    result = runner.invoke(
        cli, ["color", "change", "-d", "HUB1SERIAL", "-p", "nope", "-s", "#ff0000"]
    )

    assert result.exit_code != 0
    assert "static" in result.output  # lists what is available
    assert not any(call.request.method == "PUT" for call in responses.calls)


@responses.activate
def test_change_rejects_stored_speed_the_server_would_reject(runner: CliRunner) -> None:
    """`off` stores speed 0, outside the endpoint's 1-10 range; carrying it
    over verbatim would earn an opaque server-side rejection."""
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)

    result = runner.invoke(cli, ["color", "change", "-d", "HUB1SERIAL", "-p", "off", "-s", "#f00"])

    assert result.exit_code != 0
    assert "--speed" in result.output
    assert not any(call.request.method == "PUT" for call in responses.calls)


@responses.activate
def test_change_speed_override_unblocks_it(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)
    responses.add(responses.PUT, f"{BASE_URL}/api/color/change", json={"code": 200, "status": 1})

    result = runner.invoke(
        cli, ["color", "change", "-d", "HUB1SERIAL", "-p", "off", "-s", "#f00", "--speed", "5"]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(responses.calls[1].request.body)["speed"] == 5


@responses.activate
def test_light_color_recolors_then_activates(runner: CliRunner) -> None:
    """The two-step the convenience command exists to hide: PUT the new color
    into the profile, then POST it onto every channel."""
    responses.add(responses.GET, f"{BASE_URL}/api/color/", json=COLOR_LIST_ENVELOPE)
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)
    responses.add(responses.PUT, f"{BASE_URL}/api/color/change", json={"code": 200, "status": 1})
    responses.add(responses.POST, f"{BASE_URL}/api/color", json={"code": 200, "status": 1})

    result = runner.invoke(cli, ["light", "color", "#ff00ff"])

    assert result.exit_code == 0, result.output
    put = next(c for c in responses.calls if c.request.method == "PUT")
    magenta = {"red": 255, "green": 0, "blue": 255}
    put_body = json.loads(put.request.body)
    assert put_body["startColor"] == put_body["middleColor"] == put_body["endColor"] == magenta

    post = next(c for c in responses.calls if c.request.method == "POST")
    assert json.loads(post.request.body) == {
        "deviceId": "HUB1SERIAL",
        "channelId": -1,
        "profile": "static",
    }


@responses.activate
def test_light_color_no_apply_skips_activation(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/color/", json=COLOR_LIST_ENVELOPE)
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)
    responses.add(responses.PUT, f"{BASE_URL}/api/color/change", json={"code": 200, "status": 1})

    result = runner.invoke(cli, ["light", "color", "#ff00ff", "--no-apply"])

    assert result.exit_code == 0, result.output
    assert not any(call.request.method == "POST" for call in responses.calls)


@responses.activate
def test_light_color_unknown_profile_makes_no_writes(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/color/", json=COLOR_LIST_ENVELOPE)

    result = runner.invoke(cli, ["light", "color", "#ff00ff", "-p", "nope"])

    assert result.exit_code != 0
    assert not any(call.request.method in {"PUT", "POST"} for call in responses.calls)


@responses.activate
def test_light_color_validates_every_device_before_writing_any(runner: CliRunner) -> None:
    """A device the server would reject must not leave the *other* hubs already
    recolored -- writing device-by-device left the two a different color."""
    responses.add(responses.GET, f"{BASE_URL}/api/color/", json=TWO_HUB_LIST_ENVELOPE)
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB2SERIAL", json=SLOW_COLOR_ENVELOPE)
    responses.add(responses.PUT, f"{BASE_URL}/api/color/change", json={"code": 200, "status": 1})
    responses.add(responses.POST, f"{BASE_URL}/api/color", json={"code": 200, "status": 1})

    result = runner.invoke(cli, ["light", "color", "#ff00ff"])

    assert result.exit_code != 0
    assert "--speed" in result.output  # and the advice names an option this command has
    assert not any(call.request.method in {"PUT", "POST"} for call in responses.calls)


@responses.activate
def test_light_color_speed_option_unblocks_every_device(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/color/", json=TWO_HUB_LIST_ENVELOPE)
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB2SERIAL", json=SLOW_COLOR_ENVELOPE)
    responses.add(responses.PUT, f"{BASE_URL}/api/color/change", json={"code": 200, "status": 1})
    responses.add(responses.POST, f"{BASE_URL}/api/color", json={"code": 200, "status": 1})

    result = runner.invoke(cli, ["light", "color", "#ff00ff", "--speed", "5"])

    assert result.exit_code == 0, result.output
    puts = [c for c in responses.calls if c.request.method == "PUT"]
    posts = [c for c in responses.calls if c.request.method == "POST"]
    assert len(puts) == len(posts) == 2
    assert {json.loads(c.request.body)["deviceId"] for c in puts} == {"HUB1SERIAL", "HUB2SERIAL"}
    assert all(json.loads(c.request.body)["speed"] == 5 for c in puts)


@responses.activate
def test_light_color_failed_recolor_skips_activation_and_exits_nonzero(runner: CliRunner) -> None:
    """The server reports this failure as a 200 envelope, which the client
    doesn't raise on -- activating anyway would re-apply the *old* color and
    still report success to a `olh light color ... && ...` script."""
    responses.add(responses.GET, f"{BASE_URL}/api/color/", json=COLOR_LIST_ENVELOPE)
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)
    responses.add(responses.PUT, f"{BASE_URL}/api/color/change", json=FAILURE_ENVELOPE)
    responses.add(responses.POST, f"{BASE_URL}/api/color", json={"code": 200, "status": 1})

    result = runner.invoke(cli, ["light", "color", "#ff00ff"])

    assert result.exit_code != 0
    assert "txtInvalidSpeed" in result.output
    assert not any(call.request.method == "POST" for call in responses.calls)


@responses.activate
def test_change_failure_envelope_exits_nonzero(runner: CliRunner) -> None:
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)
    responses.add(responses.PUT, f"{BASE_URL}/api/color/change", json=FAILURE_ENVELOPE)

    result = runner.invoke(
        cli, ["color", "change", "-d", "HUB1SERIAL", "-p", "static", "-s", "#ff00ff"]
    )

    assert result.exit_code != 0


@responses.activate
def test_change_honors_the_global_json_flag(runner: CliRunner) -> None:
    """Writes are pipeable into jq too, not just reads."""
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=COLOR_ENVELOPE)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/color/change",
        json={"code": 200, "status": 1, "message": "RGB profile is successfully updated"},
    )

    result = runner.invoke(
        cli, ["-j", "color", "change", "-d", "HUB1SERIAL", "-p", "static", "-s", "#ff00ff"]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "code": 200,
        "status": 1,
        "message": "RGB profile is successfully updated",
    }


@responses.activate
def test_change_ambiguous_profile_name_makes_no_put(runner: CliRunner) -> None:
    """The payload mixes casings elsewhere, so a casefold collision is real;
    silently picking one would edit an arbitrary profile's colors."""
    both = {"code": 200, "status": 0, "data": {"profiles": {"Static": {}, "static": {}}}}
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=both)

    result = runner.invoke(
        cli, ["color", "change", "-d", "HUB1SERIAL", "-p", "static", "-s", "#ff0000"]
    )

    assert result.exit_code != 0
    assert "ambiguous" in result.output
    assert not any(call.request.method == "PUT" for call in responses.calls)


@responses.activate
def test_change_non_dict_profile_is_a_clean_error(runner: CliRunner) -> None:
    broken = {"code": 200, "status": 0, "data": {"profiles": {"static": "not an object"}}}
    responses.add(responses.GET, f"{BASE_URL}/api/color/HUB1SERIAL", json=broken)

    result = runner.invoke(
        cli, ["color", "change", "-d", "HUB1SERIAL", "-p", "static", "-s", "#ff0000"]
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, SystemExit)  # a usage error, not a traceback
    assert not any(call.request.method == "PUT" for call in responses.calls)
