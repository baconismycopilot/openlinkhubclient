import click

from olh.context import CliContext


@click.group("argb")
def argb() -> None:
    """Configure custom ARGB device ports (Commander Core, Commander Core XT)."""


@argb.command("set")
@click.option("-d", "--device-id", required=True)
@click.option("-p", "--port-id", type=int, required=True)
@click.option("-t", "--device-type", type=int, required=True)
@click.pass_obj
def set_argb(obj: CliContext, device_id: str, port_id: int, device_type: int) -> None:
    """POST /api/argb."""
    payload = {"deviceId": device_id, "portId": port_id, "deviceType": device_type}
    obj.render(obj.client.post("/api/argb", json=payload))
