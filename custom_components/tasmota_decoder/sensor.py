"""Sensor holding the latest decode-status.py report."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    ATTR_FULL_OUTPUT,
    ATTR_IP_ADDRESS,
    MAX_STATE_LENGTH,
    SENSOR_NAME,
    SENSOR_UNIQUE_ID,
    SIGNAL_OUTPUT,
    STATE_TRUNCATED,
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the output sensor from the integration's discovery call."""
    if discovery_info is None:
        return

    async_add_entities([TasmotaDecoderOutputSensor()])


class TasmotaDecoderOutputSensor(SensorEntity, RestoreEntity):
    """Last decoded Tasmota status report.

    Registered as a real entity rather than written straight into the state
    machine, so that it keeps a unique ID, survives a restart and can be
    renamed or excluded from the recorder like any other entity.
    """

    _attr_name = SENSOR_NAME
    _attr_unique_id = SENSOR_UNIQUE_ID
    _attr_icon = "mdi:script-text-outline"
    _attr_should_poll = False

    def __init__(self) -> None:
        """Initialise the sensor with no report yet."""
        self._full_output: str | None = None
        self._ip_address: str | None = None
        self._attr_native_value: str | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the last report and subscribe to new ones."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self._attr_native_value = last_state.state
            self._full_output = last_state.attributes.get(ATTR_FULL_OUTPUT)
            self._ip_address = last_state.attributes.get(ATTR_IP_ADDRESS)

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_OUTPUT, self._handle_output)
        )

    @callback
    def _handle_output(self, ip_address: str, output: str) -> None:
        """Store a freshly decoded report."""
        self._ip_address = ip_address
        self._full_output = output
        self._attr_native_value = (
            STATE_TRUNCATED if len(output) > MAX_STATE_LENGTH else output
        )
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the full report, which is far longer than a state may be."""
        return {
            ATTR_FULL_OUTPUT: self._full_output,
            ATTR_IP_ADDRESS: self._ip_address,
        }
