import click

from olh.commands._shared import JSON, yes_option
from olh.context import CliContext
from olh.output import confirm_or_abort


@click.group("temperatures")
def temperatures() -> None:
    """Manage temperature profiles (CPU/GPU/Liquid/static) and their graphs."""


@temperatures.command("list")
@click.pass_obj
def list_profiles(obj: CliContext) -> None:
    """GET /api/temperatures/."""
    obj.render(obj.client.get("/api/temperatures/"), key="data")


@temperatures.command("get")
@click.argument("profile")
@click.pass_obj
def get_profile(obj: CliContext, profile: str) -> None:
    """GET /api/temperatures/<profile>."""
    obj.render(obj.client.get(f"/api/temperatures/{profile}"), key="data")


@temperatures.command("graph")
@click.argument("profile")
@click.pass_obj
def graph(obj: CliContext, profile: str) -> None:
    """GET /api/temperatures/graph/<profile>."""
    obj.render(obj.client.get(f"/api/temperatures/graph/{profile}"), key="data")


@temperatures.command("create")
@click.option("-p", "--profile", required=True, help="New profile name.")
@click.option(
    "-s",
    "--sensor",
    type=click.Choice(["cpu", "gpu", "liquid"], case_sensitive=False),
    required=True,
)
@click.option("-S", "--static", is_flag=True, help="Create a static (non-graphed) profile.")
@click.pass_obj
def create(obj: CliContext, profile: str, sensor: str, static: bool) -> None:
    """POST /api/temperatures/new."""
    sensor_id = {"cpu": 0, "gpu": 1, "liquid": 2}[sensor.lower()]
    payload: dict[str, object] = {"profile": profile, "sensor": sensor_id}
    if static:
        payload["static"] = True
    obj.render(obj.client.post("/api/temperatures/new", json=payload))


@temperatures.command("update-graph")
@click.option("-p", "--profile", required=True)
@click.option(
    "-t",
    "--target",
    "update_type",
    type=click.Choice(["pump", "fans"]),
    required=True,
    help="Which curve to update.",
)
@click.option(
    "-P",
    "--points",
    type=JSON,
    required=True,
    help=(
        'JSON list of {"x": temp, "y": percent} points, e.g. \'[{"x":0,"y":25},{"x":60,"y":100}]\''
    ),
)
@click.pass_obj
def update_graph(obj: CliContext, profile: str, update_type: str, points: list) -> None:
    """POST /api/temperatures/updateGraph."""
    payload = {
        "profile": profile,
        "updateType": 0 if update_type == "pump" else 1,
        "points": points,
    }
    obj.render(obj.client.post("/api/temperatures/updateGraph", json=payload))


@temperatures.command("delete")
@click.argument("profile")
@yes_option
@click.pass_obj
def delete(obj: CliContext, profile: str, yes: bool) -> None:
    """DELETE /api/temperatures/delete.

    Devices currently using this profile are reset to the Normal profile.
    """
    confirm_or_abort(
        f"Delete temperature profile {profile!r}? Devices using it reset to Normal.", yes=yes
    )
    obj.render(obj.client.delete("/api/temperatures/delete", json={"profile": profile}))
