import click

from olh.context import CliContext


@click.group("hub")
def hub() -> None:
    """Configure LED strips and external hub ports (Link Hub, Commander Pro, ...)."""


@hub.command("set-strip")
@click.option("-d", "--device-id", required=True)
@click.option("-c", "--channel-id", type=int, required=True)
@click.option("-s", "--strip-id", type=int, required=True)
@click.pass_obj
def set_strip(obj: CliContext, device_id: str, channel_id: int, strip_id: int) -> None:
    """POST /api/hub/strip. Link System Hub LED strip type."""
    payload = {"deviceId": device_id, "channelId": channel_id, "stripId": strip_id}
    obj.render(obj.client.post("/api/hub/strip", json=payload))


@hub.command("set-type")
@click.option("-d", "--device-id", required=True)
@click.option("-p", "--port-id", type=int, required=True)
@click.option("-t", "--device-type", type=int, required=True)
@click.pass_obj
def set_type(obj: CliContext, device_id: str, port_id: int, device_type: int) -> None:
    """POST /api/hub/type. External LED device type (CC XT, Commander Pro, LNP)."""
    payload = {"deviceId": device_id, "portId": port_id, "deviceType": device_type}
    obj.render(obj.client.post("/api/hub/type", json=payload))


@hub.command("set-amount")
@click.option("-d", "--device-id", required=True)
@click.option("-p", "--port-id", type=int, required=True)
@click.option("-a", "--amount", "device_amount", type=int, required=True)
@click.pass_obj
def set_amount(obj: CliContext, device_id: str, port_id: int, device_amount: int) -> None:
    """POST /api/hub/amount. External LED device amount."""
    payload = {"deviceId": device_id, "portId": port_id, "deviceAmount": device_amount}
    obj.render(obj.client.post("/api/hub/amount", json=payload))
