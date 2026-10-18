# ruff: noqa: F821  (SCons provides Import and env when PlatformIO runs this script)
# PlatformIO extra script: flash using the factory StackChan partition layout.
# Arduino-ESP32 2.x hardcodes boot_app0 (OTA selector) at 0xe000; the factory
# table puts otadata at 0xd000. The app offset is set in platformio.ini.
# The upload command is already assembled when post scripts run, so patch its flags.
Import("env")

env.Replace(UPLOADERFLAGS=[
    "0xd000" if flag == "0xe000" else flag for flag in env.get("UPLOADERFLAGS", [])
])
