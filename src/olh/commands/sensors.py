import click

from olh.context import CliContext


@click.group("sensors")
def sensors() -> None:
    """Read CPU/GPU/storage temperatures and battery levels."""


@sensors.command("cpu")
@click.option(
    "-c", "--clean", is_flag=True, help="Return a bare numeric value instead of a string."
)
@click.pass_obj
def cpu(obj: CliContext, clean: bool) -> None:
    """GET /api/cpuTemp[/clean]."""
    path = "/api/cpuTemp/clean" if clean else "/api/cpuTemp"
    obj.render(obj.client.get(path), key="data")


@sensors.command("gpu")
@click.option(
    "-c", "--clean", is_flag=True, help="Return a bare numeric value instead of a string."
)
@click.pass_obj
def gpu(obj: CliContext, clean: bool) -> None:
    """GET /api/gpuTemp[/clean]."""
    path = "/api/gpuTemp/clean" if clean else "/api/gpuTemp"
    obj.render(obj.client.get(path), key="data")


@sensors.command("storage")
@click.pass_obj
def storage(obj: CliContext) -> None:
    """GET /api/storageTemp."""
    obj.render(obj.client.get("/api/storageTemp"), key="data")


@sensors.command("battery")
@click.pass_obj
def battery(obj: CliContext) -> None:
    """GET /api/batteryStats."""
    obj.render(obj.client.get("/api/batteryStats"), key="data")
