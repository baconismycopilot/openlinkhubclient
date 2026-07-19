import io

import click
import pytest
from rich.console import Console

from olh import output


@pytest.fixture
def captured_console(monkeypatch: pytest.MonkeyPatch) -> Console:
    buffer = io.StringIO()
    test_console = Console(file=buffer, force_terminal=False, width=200)
    monkeypatch.setattr(output, "console", test_console)
    return test_console


def _text(console: Console) -> str:
    return console.file.getvalue()


def test_render_json_output(captured_console: Console) -> None:
    output.render({"code": 200, "data": [1, 2]}, output_format="json")
    assert '"code": 200' in _text(captured_console)


def test_render_yaml_output(captured_console: Console) -> None:
    output.render({"code": 200, "data": [1, 2]}, output_format="yaml")
    assert "code: 200" in _text(captured_console)


def test_render_extracts_key_and_prints_table(captured_console: Console) -> None:
    response = {
        "code": 200,
        "devices": {"abc123": {"Product": "iCUE LINK System Hub"}},
    }
    output.render(response, output_format="table", key="devices")
    text = _text(captured_console)
    assert "abc123" in text
    assert "iCUE LINK System Hub" in text


def test_render_single_dict_uses_kv_layout(captured_console: Console) -> None:
    response = {"data": {"showCpu": True, "showGpu": False}}
    output.render(response, output_format="table", key="data")
    text = _text(captured_console)
    assert "showCpu" in text
    assert "True" in text


def test_render_empty_dict_prints_no_data_message(captured_console: Console) -> None:
    output.render({"code": 200, "data": {}}, output_format="table", key="data")
    assert "No data returned" in _text(captured_console)


def test_render_scalar_value(captured_console: Console) -> None:
    output.render({"data": "45.2 °C"}, output_format="table", key="data")
    assert "45.2" in _text(captured_console)


def test_render_table_summarizes_deep_nested_cells(captured_console: Console) -> None:
    """List views collapse cells that nest further dicts/lists to a count —
    the full structure belongs to the resource's `get` command."""
    response = {
        "devices": {
            "abc123": {
                "Product": "iCUE LINK System Hub",
                "profiles": {"rainbow": {"speed": 3}, "static": {"speed": 1}},
            }
        }
    }
    output.render(response, output_format="table", key="devices")
    text = _text(captured_console)
    assert "(2 fields)" in text
    assert "speed: 3" not in text


def test_render_table_keeps_flat_nested_cells(captured_console: Console) -> None:
    """A flat map of scalars (e.g. the channels column) stays fully rendered
    in list views — only *deep* nesting is summarized."""
    response = {
        "devices": {
            "abc123": {
                "Product": "iCUE LINK System Hub",
                "channels": {1: "Pump (AIO)", 2: "Front Fan (Fan)"},
            }
        }
    }
    output.render(response, output_format="table", key="devices")
    text = _text(captured_console)
    assert "Pump (AIO)" in text
    assert "(2 fields)" not in text


def test_render_kv_defers_deep_fields_to_subtables(captured_console: Console) -> None:
    """A mixed dict (a get payload) never renders deep values inline: the kv
    block gets a `see table below` marker and the deep field renders as its
    own titled table, whose deeper cells summarize again."""
    response = {
        "data": {
            "serial": "HUBSERIAL",
            "devices": {
                "1": {"ledChannels": 44, "pump": True, "channels": {"0": {"red": 0}}},
            },
        }
    }
    output.render(response, output_format="table", key="data")
    text = _text(captured_console)
    assert "see 'devices' table below" in text
    assert "44" in text  # sub-table renders the devices rows
    assert "(1 field)" in text  # ...with *their* deep cells summarized
    assert "red: 0" not in text  # per-LED detail needs a PATH drill


def test_render_kv_keeps_flat_dict_flattened(captured_console: Console) -> None:
    response = {"data": {"name": "x", "defaultColor": {"red": 255, "green": 0}}}
    output.render(response, output_format="table", key="data")
    text = _text(captured_console)
    assert "defaultColor.red" in text
    assert "255" in text


def test_render_kv_shows_empty_dict_fields(captured_console: Console) -> None:
    """An empty dict must render as a `{}` row, not silently vanish (the
    flatten loop over {} adds no rows) — same 'silent blank output' bug class
    as the empty-payload case."""
    output.render({"data": {"name": "x", "userProfiles": {}, "tags": []}}, key="data")
    text = _text(captured_console)
    assert "userProfiles" in text
    assert "tags" in text


def test_render_deferred_mixed_dict_is_bounded(captured_console: Console) -> None:
    """A deferred mixed dict (scalars alongside sub-dicts) renders one kv
    sub-table whose deep values collapse to counts — no third-level tables,
    no full-depth recursion."""
    response = {
        "data": {
            "serial": "HUBSERIAL",
            "devices": {
                "meta": "scalar",
                "1": {"channels": {"0": {"red": 1}}},
            },
        }
    }
    output.render(response, key="data")
    text = _text(captured_console)
    assert "see 'devices' table below" in text
    assert "meta" in text
    assert "(1 field)" in text  # the "1" entry's deep value, as a count
    assert "red: 1" not in text  # depth 3 is drill territory


def test_render_deferred_irregular_list_is_summarized(captured_console: Console) -> None:
    """A deferred deep list that isn't all-dicts must not fall back to a full
    inline YAML dump — each item renders as a (possibly summarized) cell."""
    output.render({"data": {"matrix": [[1, 2], [{"a": {"b": 1}}, 3]]}}, key="data")
    text = _text(captured_console)
    assert "see 'matrix' table below" in text
    assert "- 1" in text  # flat sub-list rendered as YAML
    assert "(2 items)" in text  # deep sub-list summarized to a count
    assert "b: 1" not in text


def test_markup_like_text_renders_literally(captured_console: Console) -> None:
    """API/user strings (labels, field names) containing Rich-markup-shaped
    text must render literally, not crash with MarkupError or restyle."""
    output.print_table([{"channels": {1: "Fan [/x] weird"}, "[red]label": "[/bold]oops"}])
    output.print_kv({"[/bold]weird": {"a": {"b": 1}}, "note": "[dim]x[/dim]"})
    text = _text(captured_console)
    assert "[/x]" in text
    assert "oops" in text


def test_print_ack_success_is_styled_green(captured_console: Console) -> None:
    output.print_ack({"code": 200, "status": 1})
    text = _text(captured_console)
    assert "code=200" in text


def test_print_ack_status_zero_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """The live server reports many failures as code 200 with status 0 (e.g.
    "non-existing speed profile") — those must not render in success green."""
    buffer = io.StringIO()
    styled_console = Console(file=buffer, force_terminal=True, width=200)
    monkeypatch.setattr(output, "console", styled_console)
    output.print_ack({"code": 200, "status": 0, "message": "Non-existing speed profile"})
    text = buffer.getvalue()
    assert "Non-existing speed profile" in text
    assert "\x1b[31m" in text  # red, not green
    assert "\x1b[32m" not in text


def test_confirm_or_abort_yes_skips_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(*_args: object, **_kwargs: object) -> bool:
        raise AssertionError("click.confirm should not be called when yes=True")

    monkeypatch.setattr(click, "confirm", fail_if_called)
    output.confirm_or_abort("Delete it?", yes=True)


def test_confirm_or_abort_declined_raises_abort(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(click, "confirm", lambda *_a, **_k: False)
    with pytest.raises(click.Abort):
        output.confirm_or_abort("Delete it?", yes=False)


def test_confirm_or_abort_accepted_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(click, "confirm", lambda *_a, **_k: True)
    output.confirm_or_abort("Delete it?", yes=False)
