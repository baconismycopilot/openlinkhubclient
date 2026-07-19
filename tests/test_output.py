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


def test_render_table_shows_full_nested_data(captured_console: Console) -> None:
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
    assert "rainbow" in text
    assert "speed: 3" in text
    assert "use -j/--json for detail" not in text


def test_print_ack_success_is_styled_green(captured_console: Console) -> None:
    output.print_ack({"code": 200, "status": 1})
    text = _text(captured_console)
    assert "code=200" in text


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
