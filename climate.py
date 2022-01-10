"""Support for Thermotec Aeroflow Heater."""
import logging
from datetime import datetime, timedelta

from thermotecaeroflowflexismart.client import Client

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    HVAC_MODE_HEAT,
    PRESET_HOME,
    PRESET_AWAY,
    PRESET_BOOST,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from . import ThermotecAeroflowEntity
from .const import DOMAIN, MANUFACTURER
from homeassistant.helpers import entity_platform, config_validation as cv

import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

INVALID_DEVICE_IDENTIFIER = "0.0.0.0"

PARALLEL_UPDATES = 0

ATTR_WINDOW_OPEN_DETECTION = "window_open_detection"
ATTR_ANTI_FREEZE_TEMPERATURE = "anti_freeze_temperature"

SET_WINDOW_OPEN_DETECTION_SCHEMA = {
    vol.Required(ATTR_WINDOW_OPEN_DETECTION): cv.boolean,
}

SET_ANTI_FREEZE_TEMPERATURE_SCHEMA = {
    vol.Required(ATTR_ANTI_FREEZE_TEMPERATURE): vol.All(vol.Coerce(int), vol.Range(min=0, max=17))
}

SERVICE_SET_WINDOW_OPEN_DETECTION = "set_window_open_detection"
SERVICE_SET_ANTI_FREEZE_TEMPERATURE = "set_anti_freeze_temperature"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Thermotec Heater based on config_entry."""
    client = hass.data[DOMAIN][entry.entry_id]  # type: Client

    zones = await client.get_zones_with_module_count()
    _LOGGER.debug("Zones with modules: %s", ", ".join(map(str, zones)))

    new_entities = []
    zone = 0
    for modules in zones:
        zone = zone + 1
        if modules == 0:
            _LOGGER.debug("Zone: %s is empty. Skipping", zone)
            continue

        for module in range(1, (modules + 1)):
            _LOGGER.debug("Zone: %s , Module: %s. Request module data", zone, module)

            device_identifier = INVALID_DEVICE_IDENTIFIER
            for attempt in range(4):  # UDP and Gateway are sometimes not 100% reliable. Retry 3 times
                module_data = await client.get_module_data(zone, module)
                device_identifier = module_data.get_device_identifier()
                if device_identifier != INVALID_DEVICE_IDENTIFIER:
                    break

            if device_identifier == INVALID_DEVICE_IDENTIFIER:
                _LOGGER.warning("Could not uniquely identify module after 3 attempts. Skip this module")
                continue

            _LOGGER.debug("Add module with Identifier: %s", device_identifier)
            entity = ThermotecAeroflowClimateEntity(
                client=client,
                zone=zone,
                module=module,
                identifier=device_identifier,
            )
            new_entities.append(entity)

    if new_entities:
        async_add_entities(new_entities, update_before_add=True)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_SET_WINDOW_OPEN_DETECTION, SET_WINDOW_OPEN_DETECTION_SCHEMA, SERVICE_SET_WINDOW_OPEN_DETECTION
    )

    platform.async_register_entity_service(
        SERVICE_SET_ANTI_FREEZE_TEMPERATURE, SET_ANTI_FREEZE_TEMPERATURE_SCHEMA, SERVICE_SET_ANTI_FREEZE_TEMPERATURE
    )


class ThermotecAeroflowClimateEntity(ThermotecAeroflowEntity, ClimateEntity):
    """Representation of a Thermotec Aeroflow heater."""

    _boost_active: bool = False
    _boost_time_left: str = "0 min"
    _holiday_mode_active: bool = False
    _sw_version: str = "Unknown"
    _date_time = None
    _window_open_detection: bool = False
    _anti_freeze_temperature: float = 0.0
    _temperature_offset: float = 0.0

    def __init__(self, client: Client, zone: int, module: int, identifier: str):
        """Initialize the climate device."""
        entity_type = "Heater"
        super().__init__(client, entity_type, zone, module, identifier)

    async def _update_status(self):
        _LOGGER.debug("Update Status called for Zone: %s and Module: %s", self._zone, self._module)

        client = self._client
        module = self._module
        zone = self._zone

        temperature = await client.get_module_temperature(zone=zone, module=module)

        self._attr_current_temperature = temperature.get_current_temperature()
        self._attr_target_temperature = temperature.get_target_temperature()

        device_data = await client.get_module_data(zone=zone, module=module)

        boost_time_left = device_data.get_boost_time_left_string()
        if not device_data.is_boost_active():
            boost_time_left = "0 min"

        self._boost_time_left = boost_time_left
        self._boost_active = device_data.is_boost_active()
        self._temperature_offset = device_data.get_temperature_offset()
        self._window_open_detection = device_data.is_window_open_detection_enabled()
        self._sw_version = device_data.get_firmware_version().replace("v", "")

        self._anti_freeze_temperature = await client.get_module_anti_freeze_temperature(zone=zone, module=module)

        holiday_data = await client.get_module_holiday_mode(zone=zone, module=module)
        self._holiday_mode_active = holiday_data.is_holiday_mode_active()

        device_data = await client.get_date_time()
        date = device_data.get_date()
        time = device_data.get_time()

        date_time = datetime.strptime(f"{date} {time}", "%d.%m.%Y %H:%M:%S")
        self._date_time = datetime.fromtimestamp(date_time.timestamp(), date_time.astimezone().tzinfo)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return 1

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return 35

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
            _LOGGER.error("Missing target temperature %s", kwargs)
            return
        target_temp = float(target_temp)
        _LOGGER.debug("Set %s temperature %s", self.entity_id, target_temp)
        # Limit the target temperature into acceptable range.
        target_temp = min(self.max_temp, target_temp)
        target_temp = max(self.min_temp, target_temp)

        await self._client.set_module_temperature(
            zone=self._zone, module=self._module, temperature=target_temp
        )

    @property
    def preset_mode(self):
        """Return the preset_mode."""
        if self._boost_active:
            return PRESET_BOOST
        if self._holiday_mode_active:
            return PRESET_AWAY

        return PRESET_HOME

    async def async_set_preset_mode(self, preset_mode):
        """Set preset mode."""
        if preset_mode == PRESET_AWAY:
            _LOGGER.debug("Activate Holiday mode")
            holiday_date = datetime.now() + timedelta(
                days=240  # max holiday length is 240 days
            )
            if self.preset_mode == PRESET_BOOST:
                await self._client.set_module_boost(self._zone, self._module, 0)

            # target_temperature is the new temperature when holiday mode ends (manually or automatically)
            await self._client.set_module_holiday_mode(
                self._zone, self._module, holiday_date, self.target_temperature
            )
        elif preset_mode == PRESET_BOOST:
            _LOGGER.debug("Activate Boost")
            if self.preset_mode == PRESET_AWAY:
                await self._client.disable_module_holiday_mode(self._zone, self._module)

            boost_timer = 95  # 95 minutes is the max boost value
            await self._client.set_module_boost(self._zone, self._module, boost_timer)
        elif preset_mode == PRESET_HOME:
            _LOGGER.debug("Go back to normal Mode")
            if self.preset_mode == PRESET_BOOST:
                _LOGGER.debug("Disable Boost mode")
                await self._client.set_module_boost(self._zone, self._module, 0)
            elif self.preset_mode == PRESET_AWAY:
                _LOGGER.debug("Disable Holiday mode")
                await self._client.disable_module_holiday_mode(self._zone, self._module)

    @property
    def preset_modes(self):
        """List of available preset modes."""
        return [PRESET_HOME, PRESET_AWAY, PRESET_BOOST]

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        _LOGGER.debug("Set %s heat mode %s", self.entity_id, hvac_mode)

    @property
    def hvac_mode(self):
        """Return hvac operation."""
        return HVAC_MODE_HEAT

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        return [HVAC_MODE_HEAT]

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        if self.current_temperature < self.target_temperature:
            return CURRENT_HVAC_HEAT
        return CURRENT_HVAC_IDLE

    async def set_window_open_detection(self, window_open_detection: bool) -> None:
        """Enable or Disable Window Open Detection."""
        _LOGGER.debug("Set %s Window Open Detection %s", self.name, window_open_detection)
        if window_open_detection:
            await self._client.enable_module_window_open_detection(zone=self._zone, module=self._module)
        else:
            await self._client.disable_module_window_open_detection(zone=self._zone, module=self._module)

    async def set_anti_freeze_temperature(self, anti_freeze_temperature: int) -> None:
        """Update Anti Freeze Temperature."""
        _LOGGER.debug("Set %s Anti Freeze Temperature %s", self.name, anti_freeze_temperature)

        await self._client.set_module_anti_freeze_temperature(
            zone=self._zone,
            module=self._module,
            temperature=float(anti_freeze_temperature)
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sun."""
        return {
            "date_time": self._date_time.isoformat(),
            "window_open_detection": self._window_open_detection,
            "anti_freeze_temperature": self._anti_freeze_temperature,
            "boost_time_left": self._boost_time_left,
            "temperature_offset": self._temperature_offset,
            "zone": self._zone,
            "module": self._module
        }

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "identifiers": {(DOMAIN, f"thermotec-aeroflow_{self._identifier}")},
            "name": self.name,
            "manufacturer": MANUFACTURER,
            "sw_version": self._sw_version,
        }
