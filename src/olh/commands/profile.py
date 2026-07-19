import click

from olh.commands._shared import rgb_options
from olh.context import CliContext


@click.group("profile")
def profile() -> None:
    """Manage per-device user profiles and misc-device (MM700/ST100) colors."""


@profile.command("change-user")
@click.option("-d", "--device-id", required=True)
@click.option("-n", "--name", "user_profile_name", required=True)
@click.pass_obj
def change_user(obj: CliContext, device_id: str, user_profile_name: str) -> None:
    """POST /api/userProfile/change."""
    payload = {"deviceId": device_id, "userProfileName": user_profile_name}
    obj.render(obj.client.post("/api/userProfile/change", json=payload))


@profile.command("save-user")
@click.option("-d", "--device-id", required=True)
@click.option("-n", "--name", "user_profile_name", required=True)
@click.pass_obj
def save_user(obj: CliContext, device_id: str, user_profile_name: str) -> None:
    """PUT /api/userProfile."""
    payload = {"deviceId": device_id, "userProfileName": user_profile_name}
    obj.render(obj.client.put("/api/userProfile", json=payload))


@profile.command("set-misc-color")
@click.option("-d", "--device-id", required=True)
@click.option("-a", "--area-id", type=int, required=True)
@click.option(
    "-s",
    "--scope",
    "area_option",
    type=click.Choice(["current-area", "current-row", "all-rows"]),
    required=True,
)
@rgb_options
@click.pass_obj
def set_misc_color(
    obj: CliContext,
    device_id: str,
    area_id: int,
    area_option: str,
    red: int,
    green: int,
    blue: int,
) -> None:
    """POST /api/misc/color. For MM700/ST100-style devices."""
    scope_code = {"current-area": 0, "current-row": 1, "all-rows": 2}[area_option]
    payload = {
        "deviceId": device_id,
        "areaId": area_id,
        "areaOption": scope_code,
        "color": {"red": red, "green": green, "blue": blue},
    }
    obj.render(obj.client.post("/api/misc/color", json=payload))
