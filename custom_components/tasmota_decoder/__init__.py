"""The Tasmota Decoder integration.

Exposes a single service, ``tasmota_decoder.run_script``, which runs the
bundled ``decode-status.py`` against a Tasmota device and publishes the
decoded report on the ``sensor.tasmota_script_output`` entity.
"""

from __future__ import annotations

import ipaddress
import logging
import subprocess
import sys
from pathlib import Path

import voluptuous as vol

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_IP_ADDRESS,
    DOMAIN,
    SCRIPT_NAME,
    SCRIPT_TIMEOUT,
    SERVICE_RUN_SCRIPT,
    SIGNAL_OUTPUT,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

SCRIPT_PATH = Path(__file__).parent / SCRIPT_NAME


def _valid_ip_address(value: object) -> str:
    """Validate that the value is a bare IP address.

    Without this check any string gets through -- including the literal
    ``unavailable`` that ``states()`` returns for a missing entity -- and ends
    up being resolved as a hostname, which fails deep inside urllib3 with an
    unhelpful traceback.
    """
    text = cv.string(value).strip()
    try:
        return str(ipaddress.ip_address(text))
    except ValueError as err:
        raise vol.Invalid(
            f"'{text}' is not a valid IP address; pass the device address only, "
            "for example 192.168.1.48"
        ) from err


SERVICE_SCHEMA = vol.Schema({vol.Required(CONF_IP_ADDRESS): _valid_ip_address})


def _run_decode_status(ip_address: str) -> str:
    """Run decode-status.py and return its output.

    Blocking; always called through the executor.
    """
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "-d", ip_address],
            capture_output=True,
            text=True,
            timeout=SCRIPT_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as err:
        raise HomeAssistantError(
            f"Timed out after {SCRIPT_TIMEOUT}s while querying {ip_address}. "
            "Is the device powered on?"
        ) from err
    except OSError as err:
        raise HomeAssistantError(f"Could not run {SCRIPT_NAME}: {err}") from err

    if result.returncode != 0:
        # The raw traceback belongs in the log, never in the entity state:
        # the dashboard renders that state verbatim.
        _LOGGER.error(
            "%s exited with code %s for %s:\n%s",
            SCRIPT_NAME,
            result.returncode,
            ip_address,
            result.stderr.strip(),
        )
        raise HomeAssistantError(
            f"Could not read the Tasmota status from {ip_address}. "
            "Check that the device is online and reachable; "
            "the full error is in the Home Assistant log."
        )

    return result.stdout.strip()


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Tasmota Decoder integration."""

    async def handle_run_script(call: ServiceCall) -> None:
        """Decode the status of the device at the requested address."""
        ip_address: str = call.data[CONF_IP_ADDRESS]
        output = await hass.async_add_executor_job(_run_decode_status, ip_address)
        async_dispatcher_send(hass, SIGNAL_OUTPUT, ip_address, output)

    hass.services.async_register(
        DOMAIN, SERVICE_RUN_SCRIPT, handle_run_script, schema=SERVICE_SCHEMA
    )

    hass.async_create_task(
        async_load_platform(hass, Platform.SENSOR, DOMAIN, {}, config)
    )

    return True
