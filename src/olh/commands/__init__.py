"""All command groups, collected for registration on the root CLI group."""

from olh.commands.apply import apply_profile
from olh.commands.argb import argb
from olh.commands.brightness import brightness
from olh.commands.color import color
from olh.commands.dashboard import dashboard
from olh.commands.devices import devices
from olh.commands.fan import fan
from olh.commands.headset import headset
from olh.commands.hub import hub
from olh.commands.input_keys import input_keys
from olh.commands.keyboard import keyboard
from olh.commands.lcd import lcd
from olh.commands.led import led
from olh.commands.light import light
from olh.commands.macro import macro
from olh.commands.media import media
from olh.commands.mouse import mouse
from olh.commands.profile import profile
from olh.commands.psu import psu
from olh.commands.scheduler import scheduler
from olh.commands.sensors import sensors
from olh.commands.speed import speed
from olh.commands.status import status
from olh.commands.temperatures import temperatures

# The convenience layer: groups (fan, light) and bare commands (status,
# apply_profile) mix freely here — cli.add_command takes any click.Command.
ALL_GROUPS = [
    fan,
    light,
    status,
    apply_profile,
    devices,
    sensors,
    color,
    led,
    speed,
    temperatures,
    macro,
    dashboard,
    input_keys,
    keyboard,
    mouse,
    headset,
    hub,
    lcd,
    brightness,
    argb,
    psu,
    scheduler,
    profile,
    media,
]
