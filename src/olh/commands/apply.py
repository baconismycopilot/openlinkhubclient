import click

from olh.commands._resolve import iter_hub_devices, match_canonical
from olh.context import CliContext
from olh.output import print_ack


@click.command("apply")
@click.argument("profile_name")
@click.option(
    "-d",
    "--device-id",
    default=None,
    help="Only needed when more than one device has saved user profiles.",
)
@click.pass_obj
def apply_profile(obj: CliContext, profile_name: str, device_id: str | None) -> None:
    """Switch to a saved user profile (POST /api/userProfile/change), resolving
    the device automatically when only one has user profiles."""
    envelope = obj.client.get("/api/devices/")
    candidates: dict[str, dict] = {}  # deviceId -> userProfiles map
    for serial, get_device in iter_hub_devices(envelope):
        profiles = get_device.get("userProfiles")
        if isinstance(profiles, dict) and profiles:
            candidates[serial] = profiles

    if device_id is not None:
        if device_id not in candidates:
            raise click.UsageError(
                f"Device {device_id!r} has no user profiles. "
                f"Devices with profiles: {', '.join(sorted(candidates)) or 'none'}."
            )
        target = device_id
    elif not candidates:
        raise click.UsageError("No device has saved user profiles.")
    elif len(candidates) > 1:
        raise click.UsageError(
            f"Several devices have user profiles: {', '.join(sorted(candidates))}. "
            "Pick one with -d/--device-id."
        )
    else:
        target = next(iter(candidates))

    canonical = match_canonical(
        profile_name, candidates[target], "user profile", f" on device {target}"
    )
    payload = {"deviceId": target, "userProfileName": canonical}
    print_ack(obj.client.post("/api/userProfile/change", json=payload))
