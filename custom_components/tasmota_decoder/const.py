"""Constants for the Tasmota Decoder integration."""

from __future__ import annotations

DOMAIN = "tasmota_decoder"

SERVICE_RUN_SCRIPT = "run_script"

CONF_IP_ADDRESS = "ip_address"

# Bundled copy of Theo Arends' decode-status.py (GPL v3, see LICENSE).
SCRIPT_NAME = "decode-status.py"

# A Tasmota device that is powered on answers in well under a second. Anything
# longer than this means it is unreachable, so do not tie up an executor thread.
SCRIPT_TIMEOUT = 30

SENSOR_NAME = "Tasmota script output"
SENSOR_UNIQUE_ID = "tasmota_decoder_script_output"

SIGNAL_OUTPUT = f"{DOMAIN}_output"

# Home Assistant refuses to store a state longer than 255 characters.
MAX_STATE_LENGTH = 255
STATE_TRUNCATED = "Output too long, see attributes"

ATTR_FULL_OUTPUT = "full_output"
ATTR_IP_ADDRESS = "ip_address"
