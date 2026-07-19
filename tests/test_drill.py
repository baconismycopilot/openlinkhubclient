"""Pure-unit coverage of the PATH walker shared by the get commands."""

import click
import pytest

from olh.commands._shared import drill


def test_drill_walks_dicts_and_lists() -> None:
    payload = {"devices": {"1": {"channels": [{"red": 5}]}}}
    assert drill(payload, ("devices", "1", "channels", "0", "red")) == 5


def test_drill_matches_case_insensitively() -> None:
    assert drill({"userProfiles": {"Default": 1}}, ("USERPROFILES",)) == {"Default": 1}


def test_drill_prefers_exact_match_over_casefold() -> None:
    payload = {"Profile": "A", "profile": "B"}
    assert drill(payload, ("profile",)) == "B"
    assert drill(payload, ("Profile",)) == "A"


def test_drill_ambiguous_casefold_errors() -> None:
    with pytest.raises(click.UsageError, match="ambiguous"):
        drill({"Profile": "A", "profile": "B"}, ("PROFILE",))


def test_drill_unknown_key_lists_available() -> None:
    with pytest.raises(click.UsageError, match="No field 'nope' in the payload"):
        drill({"a": 1, "b": 2}, ("nope",))


def test_drill_bad_list_index_names_where() -> None:
    with pytest.raises(click.UsageError, match="items is a list of 2 items"):
        drill({"items": [1, 2]}, ("items", "9"))


def test_drill_scalar_node_errors() -> None:
    with pytest.raises(click.UsageError, match="cannot drill into"):
        drill({"a": 5}, ("a", "deeper"))
