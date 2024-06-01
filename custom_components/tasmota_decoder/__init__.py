import logging
import subprocess
import os
import voluptuous as vol

from homeassistant.helpers import config_validation as cv

DOMAIN = "tasmota_decoder"

_LOGGER = logging.getLogger(__name__)

CONF_IP_ADDRESS = "ip_address"

SERVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): cv.string,
})

def setup(hass, config):
    def handle_run_script(call):
        ip_address = call.data[CONF_IP_ADDRESS]
        script_path = os.path.join(os.path.dirname(__file__), "decode-status.py")

        result = subprocess.run(
            ["python3", script_path, "-d", ip_address],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            output = f"Error: {result.stderr}"
            _LOGGER.error(output)
        else:
            output = result.stdout.strip()

        # Ensure the state itself is within the allowed limit
        state = "Output too long, see attributes" if len(output) > 255 else output

        # Update the sensor with a short state and full output as an attribute
        hass.states.set('sensor.tasmota_script_output', state, {'full_output': output})

    hass.services.register(DOMAIN, 'run_script', handle_run_script, schema=SERVICE_SCHEMA)

    return True