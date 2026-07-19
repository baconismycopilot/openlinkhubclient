"""Unit tests for the name→id resolution helpers behind fan/light/status/apply.
No HTTP here — resolution logic is exercised on hand-built Channel lists;
the HTTP-level plumbing is covered in test_cli_convenience.py."""

import click
import pytest

from olh.commands._resolve import (
    Channel,
    fetch_channels,
    parse_speed_value,
    resolve_channel,
    resolve_targets,
)


def make_channel(**overrides) -> Channel:
    defaults = {
        "device_id": "HUB1",
        "channel_id": 1,
        "label": "GPU Intake 1",
        "name": "iCUE LINK QX RGB",
        "description": "Fan",
        "profile": "Normal",
        "rgb": "static",
        "has_speed": True,
        "rpm": 600,
        "temperature": "22.5 °C",
    }
    defaults.update(overrides)
    return Channel(**defaults)


CHANNELS = [
    make_channel(channel_id=1, label="GPU Intake 1"),
    make_channel(channel_id=2, label="GPU Intake 2"),
    make_channel(channel_id=3, label="H150i Pump", description="Pump"),
    make_channel(device_id="HUB2", channel_id=1, label="Rear Fan"),
]


class TestParseSpeedValue:
    def test_percent_suffix(self) -> None:
        assert parse_speed_value("50%") == 50

    def test_bare_integer(self) -> None:
        assert parse_speed_value("50") == 50

    def test_zero(self) -> None:
        assert parse_speed_value("0") == 0

    @pytest.mark.parametrize("text", ["101", "150%", "-5"])
    def test_out_of_range_raises(self, text: str) -> None:
        with pytest.raises(click.UsageError):
            parse_speed_value(text)

    def test_non_numeric_means_profile_name(self) -> None:
        assert parse_speed_value("Quiet") is None


class TestResolveChannel:
    def test_exact_label(self) -> None:
        assert resolve_channel(CHANNELS, "gpu intake 1").channel_id == 1

    def test_description_resolves_pump(self) -> None:
        assert resolve_channel(CHANNELS, "pump").channel_id == 3

    def test_pump_matches_aio_description(self) -> None:
        # A real AIO's pump channel reports description "AIO", not "Pump".
        channels = [
            make_channel(channel_id=1, label="Set Label", description="AIO"),
            make_channel(channel_id=2, label="Set Label", description="Fan"),
        ]
        assert resolve_channel(channels, "pump").channel_id == 1

    def test_literal_channel_id(self) -> None:
        assert resolve_channel(CHANNELS, "3").label == "H150i Pump"

    def test_substring_when_unambiguous(self) -> None:
        assert resolve_channel(CHANNELS, "rear").device_id == "HUB2"

    def test_exact_label_beats_substring(self) -> None:
        channels = [
            make_channel(channel_id=5, label="Front"),
            make_channel(channel_id=6, label="Front Top"),
        ]
        assert resolve_channel(channels, "front").channel_id == 5

    def test_ambiguous_substring_names_all_matches(self) -> None:
        with pytest.raises(click.UsageError, match=r"GPU Intake 1.*GPU Intake 2"):
            resolve_channel(CHANNELS, "intake")

    def test_ambiguous_channel_id_across_hubs(self) -> None:
        with pytest.raises(click.UsageError, match="ambiguous"):
            resolve_channel(CHANNELS, "1")

    def test_no_match_lists_available(self) -> None:
        with pytest.raises(click.UsageError, match="H150i Pump"):
            resolve_channel(CHANNELS, "nonsense")


class TestResolveTargets:
    def test_all_fans_out_per_device_with_sentinel(self) -> None:
        assert resolve_targets(CHANNELS, "all") == [("HUB1", -1), ("HUB2", -1)]

    def test_single_name_resolves_one_pair(self) -> None:
        assert resolve_targets(CHANNELS, "pump") == [("HUB1", 3)]


class TestFetchChannels:
    def test_skips_devices_without_channel_maps(self) -> None:
        class FakeClient:
            def get(self, path: str):
                return {
                    "code": 200,
                    "devices": {
                        "HUB1": {
                            "Serial": "HUB1",
                            "GetDevice": {
                                "devices": {
                                    "1": {
                                        "channelId": 1,
                                        "label": "Fan 1",
                                        "description": "Fan",
                                        "HasSpeed": True,
                                    }
                                }
                            },
                        },
                        "MOUSE": {"Serial": "MOUSE", "GetDevice": None},
                        "DONGLE": {"Serial": "DONGLE", "GetDevice": {"product": "dongle"}},
                    },
                }

        channels = fetch_channels(FakeClient())
        assert [c.label for c in channels] == ["Fan 1"]
        assert channels[0].device_id == "HUB1"
