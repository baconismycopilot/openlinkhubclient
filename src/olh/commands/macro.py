import click

from olh.commands._shared import yes_option
from olh.context import CliContext
from olh.output import confirm_or_abort


@click.group("macro")
def macro() -> None:
    """Manage macros and their action sequences."""


@macro.command("list")
@click.pass_obj
def list_macros(obj: CliContext) -> None:
    """GET /api/macro/."""
    obj.render(obj.client.get("/api/macro/"), key="data")


@macro.command("get")
@click.argument("macro_id", type=int)
@click.pass_obj
def get_macro(obj: CliContext, macro_id: int) -> None:
    """GET /api/macro/<macro_id>."""
    obj.render(obj.client.get(f"/api/macro/{macro_id}"), key="data")


@macro.command("create")
@click.option("-n", "--name", "macro_name", required=True)
@click.pass_obj
def create(obj: CliContext, macro_name: str) -> None:
    """PUT /api/macro/new."""
    obj.render(obj.client.put("/api/macro/new", json={"macroName": macro_name}))


@macro.command("add-value")
@click.option("-m", "--macro-id", type=int, required=True)
@click.option("-t", "--type", "macro_type", type=int, required=True, help="Action type code.")
@click.option("-v", "--value", "macro_value", type=int, required=True, help="Key/command code.")
@click.option(
    "-e", "--delay", "macro_delay", type=int, default=0, help="Delay in ms after the action."
)
@click.pass_obj
def add_value(
    obj: CliContext, macro_id: int, macro_type: int, macro_value: int, macro_delay: int
) -> None:
    """POST /api/macro/newValue."""
    payload = {
        "macroId": macro_id,
        "macroType": macro_type,
        "macroValue": macro_value,
        "macroDelay": macro_delay,
    }
    obj.render(obj.client.post("/api/macro/newValue", json=payload))


@macro.command("delete-value")
@click.option("-m", "--macro-id", type=int, required=True)
@click.option("-i", "--index", "macro_index", type=int, required=True)
@yes_option
@click.pass_obj
def delete_value(obj: CliContext, macro_id: int, macro_index: int, yes: bool) -> None:
    """DELETE /api/macro/value."""
    confirm_or_abort(f"Delete action {macro_index} from macro {macro_id}?", yes=yes)
    payload = {"macroId": macro_id, "macroIndex": macro_index}
    obj.render(obj.client.delete("/api/macro/value", json=payload))


@macro.command("delete")
@click.argument("macro_id", type=int)
@yes_option
@click.pass_obj
def delete(obj: CliContext, macro_id: int, yes: bool) -> None:
    """DELETE /api/macro/profile."""
    confirm_or_abort(f"Delete macro {macro_id} entirely?", yes=yes)
    obj.render(obj.client.delete("/api/macro/profile", json={"macroId": macro_id}))
