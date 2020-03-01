"""Platform for light integration."""
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchDevice
from homeassistant.const import (SERVICE_TOGGLE, SERVICE_TURN_OFF, SERVICE_TURN_ON)

# from homeassistant.components.switch import

_LOGGER = logging.getLogger(__name__)

REMOTE_NAME = "remote"
REMOTE_ACTION = "action"

EMPTY_REMOTE = {REMOTE_ACTION: "", REMOTE_NAME: ""}

REMOTE_CONFIG = vol.Schema(
    {
        vol.Required(REMOTE_NAME, default=""): cv.string,
        vol.Required(REMOTE_ACTION, default=""): cv.string,
    }
)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required("name"): cv.string,
        vol.Required(SERVICE_TURN_ON, default=EMPTY_REMOTE): REMOTE_CONFIG,
        vol.Optional(SERVICE_TURN_OFF, default=EMPTY_REMOTE): REMOTE_CONFIG,
        vol.Optional(SERVICE_TOGGLE, default=EMPTY_REMOTE): REMOTE_CONFIG,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Awesome Light platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.
    name = config["name"]
    remotes = {
        SERVICE_TURN_ON: config.get(SERVICE_TURN_ON),
        SERVICE_TURN_OFF: config.get(SERVICE_TURN_OFF),
        SERVICE_TOGGLE: config.get(SERVICE_TOGGLE),
    }

    # Add devices
    add_entities([UnifiedSwitch(hass, name, remotes)])


class UnifiedSwitch(SwitchDevice):
    def __init__(self, hass, name, remotes):
        self._switch_name = name
        self._remotes = remotes
        self.hass = hass
        self.call = self.hass.services.call
        self._state = False

    def turn_on(self) -> None:
        """Turn the entity on."""
        remote = self._remotes.get(SERVICE_TURN_ON)
        if remote != EMPTY_REMOTE:
            self.call(domain="unified_remote", service="call", service_data=remote)
            self._state = True

    def turn_off(self):
        """Turn the entity off."""
        remote = self._remotes.get(SERVICE_TURN_OFF)
        if remote != EMPTY_REMOTE:
            self.call(domain="unified_remote", service="call", service_data=remote)
            self._state = False

    def toggle(self):
        """Toggle the entity."""
        remote = self._remotes.get(SERVICE_TOGGLE)
        if remote != EMPTY_REMOTE:
            self.call(domain="unified_remote", service="call", service_data=remote)
            self._state = not self._state

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._switch_name

    @property
    def is_on(self):
        return self._state
