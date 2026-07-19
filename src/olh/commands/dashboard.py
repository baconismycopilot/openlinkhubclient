import click

from olh.context import CliContext


@click.group("dashboard")
def dashboard() -> None:
    """View and update web UI dashboard display settings."""


@dashboard.command("show")
@click.pass_obj
def show(obj: CliContext) -> None:
    """GET /api/dashboard."""
    obj.render(obj.client.get("/api/dashboard"), key="dashboard")


@dashboard.command("update")
@click.option("-c", "--show-cpu/--no-show-cpu", default=None)
@click.option("-g", "--show-gpu/--no-show-gpu", default=None)
@click.option("-k", "--show-disk/--no-show-disk", default=None)
@click.option("-e", "--show-devices/--no-show-devices", default=None)
@click.option("-l", "--show-labels/--no-show-labels", default=None)
@click.option("-b", "--show-battery/--no-show-battery", default=None)
@click.option("-u", "--celsius/--fahrenheit", default=None)
@click.option("-v", "--vertical-ui/--horizontal-ui", default=None)
@click.pass_obj
def update(
    obj: CliContext,
    show_cpu: bool | None,
    show_gpu: bool | None,
    show_disk: bool | None,
    show_devices: bool | None,
    show_labels: bool | None,
    show_battery: bool | None,
    celsius: bool | None,
    vertical_ui: bool | None,
) -> None:
    """POST /api/dashboard/update.

    OpenLinkHub's update endpoint replaces the whole settings object rather
    than patching it: any field missing from the request body gets reset to
    its zero value (confirmed against a live instance, where posting only
    the fields below silently zeroed out unrelated settings). To make this
    command safe to use for a single setting, it first GETs the current
    dashboard, overlays only the flags you passed, and posts the full
    merged object back.
    """
    overrides = {
        "showCpu": show_cpu,
        "showGpu": show_gpu,
        "showDisk": show_disk,
        "showDevices": show_devices,
        "showLabels": show_labels,
        "showBattery": show_battery,
        "celsius": celsius,
        "verticalUi": vertical_ui,
    }
    overrides = {key: value for key, value in overrides.items() if value is not None}
    if not overrides:
        raise click.UsageError("Pass at least one --show-*/--no-show-* flag to update.")

    current = obj.client.get("/api/dashboard")
    payload = {**current.get("dashboard", {}), **overrides}
    obj.render(obj.client.post("/api/dashboard/update", json=payload))
