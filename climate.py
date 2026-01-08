"""Support for Thermotec Aeroflow Heater."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol
from thermotecaeroflowflexismart.client import Client
from thermotecaeroflowflexismart.data_object import HomeAssistantModuleData

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACAction,
    HVACMode,
    PRESET_HOME,
    PRESET_AWAY,
    PRESET_BOOST,
    ClimateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ThermotecAeroflowEntity
from .const import DOMAIN, MANUFACTURER
from .coordinator import ThermotecDeviceCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

SET_WINDOW_OPEN_DETECTION_SCHEMA = {
    vol.Required("window_open_detection"): cv.boolean,
}

SET_ANTI_FREEZE_TEMPERATURE_SCHEMA = {
    vol.Required("anti_freeze_temperature"): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=17)
    )
}

SET_TEMPERATURE_SCHEMA = {
    vol.Required(ATTR_TEMPERATURE): vol.All(
        vol.Coerce(float), vol.Range(min=1, max=35)
    )
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Thermotec Heater based on config_entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    client = entry_data["client"]  # type: Client
    zones_coordinator = entry_data["zones_coordinator"]
    device_coordinators = entry_data["device_coordinators"]  # type: dict
    extended_data = entry_data["extended_data"]

    entities = []

    # Get initial zone list from zones coordinator
    zones = zones_coordinator.data or []
    
    # For each zone, create climate entities for all modules
    for zone in zones:
        # This assumes the client can provide module count per zone
        # Adjust based on actual API
        try:
            module_count = await client.get_module_count(zone=zone)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Could not get module count for zone %s: %s", zone, err)
            module_count = 1  # Default to 1 module

        for module in range(1, module_count + 1):
            identifier = f"zone_{zone}_module_{module}"
            
            # Create device coordinator for this specific device
            device_coordinator = ThermotecDeviceCoordinator(
                hass,
                client,
                zone=zone,
                module=module,
                extended_data=extended_data,
            )
            device_coordinators[identifier] = device_coordinator
            
            # Perform initial refresh
            try:
                await device_coordinator.async_config_entry_first_refresh()
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.warning(
                    "Failed to fetch initial data for zone %s, module %s: %s",
                    zone,
                    module,
                    err,
                )

            entities.append(
                ThermotecAeroflowClimateEntity(
                    device_coordinator,
                    client,
                    identifier,
                    zone,
                    module,
                )
            )

    async_add_entities(entities)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "set_window_open_detection",
        SET_WINDOW_OPEN_DETECTION_SCHEMA,
        "set_window_open_detection",
    )

    platform.async_register_entity_service(
        "set_anti_freeze_temperature",
        SET_ANTI_FREEZE_TEMPERATURE_SCHEMA,
        "set_anti_freeze_temperature",
    )

    platform.async_register_entity_service(
        "set_temperature", SET_TEMPERATURE_SCHEMA, "async_set_temperature"
    )


class ThermotecAeroflowClimateEntity(ThermotecAeroflowEntity, ClimateEntity):
    """Representation of a Thermotec Aeroflow heater."""

    _boost_active: bool = False
    _boost_time_left: str = "0 min"
    _holiday_mode_active: bool = False
    _sw_version: str = "Unknown"
    _window_open_detection: bool = False
    _anti_freeze_temperature: float = 0.0
    _temperature_offset: float = 0.0

    _attr_min_temp = 1
    _attr_max_temp = 35
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_preset_modes = [PRESET_HOME, PRESET_AWAY, PRESET_BOOST]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_hvac_modes = [HVACMode.HEAT]

    def __init__(
        self,
        coordinator: ThermotecDeviceCoordinator,
        client: Client,
        identifier: str,
        zone: int,
        module: int,
    ):
        """Initialize the climate device."""
        entity_type = "Heater"
        super().__init__(
            coordinator=coordinator,
            client=client,
            entity_type=entity_type,
            zone=zone,
            module=module,
            identifier=identifier,
        )
        self._update_attributes()

    def _update_attributes(self) -> None:
        """Update entity attributes from coordinator data."""
        _LOGGER.debug("Updating %s", self._identifier)

        current_data = self.coordinator.data
        if current_data is None:
            _LOGGER.debug(
                "Could not find data for heater with identifier %s. Marking unavailable.",
                self._identifier,
            )
            self._attr_available = False
            return

        self._attr_available = True

        # Handle both direct module data and HomeAssistantModuleData
        if isinstance(current_data, HomeAssistantModuleData):
            module_data = current_data.get_module_data()
        else:
            module_data = current_data

        self._attr_target_temperature = module_data.get_target_temperature()
        self._attr_current_temperature = module_data.get_current_temperature()

        boost_time_left = module_data.get_boost_time_left_string()
        if not module_data.is_boost_active():
            boost_time_left = "0 min"

        self._boost_time_left = boost_time_left
        self._boost_active = module_data.is_boost_active()
        self._temperature_offset = module_data.get_temperature_offset()
        self._window_open_detection = module_data.is_window_open_detection_enabled()
        self._sw_version = module_data.get_firmware_version().replace("v", "")

        # Get anti-freeze temperature if available
        if isinstance(current_data, HomeAssistantModuleData):
            anti_freeze_temperature = current_data.get_anti_freeze_temperature()
            if anti_freeze_temperature is not None:
                self._anti_freeze_temperature = anti_freeze_temperature

            holiday_data = current_data.get_holiday_data()
            if holiday_data is not None:
                self._holiday_mode_active = holiday_data.is_holiday_mode_active()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attributes()
        # Mark device as available if we got data
        if self.coordinator.data is not None:
            self.coordinator.mark_available()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.is_available
            and self._attr_available
        )

    @property
    def preset_mode(self) -> str | None:
        """Return the preset_mode."""
        if self._boost_active:
            return PRESET_BOOST
        if self._holiday_mode_active:
            return PRESET_AWAY

        return PRESET_HOME

    async def async_set_temperature(self, **kwargs: Any) -> None:
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

        self._attr_target_temperature = target_temp
        await self.async_update_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        if preset_mode == PRESET_AWAY:
            _LOGGER.debug("Activate Holiday mode")
            holiday_date = datetime.now() + timedelta(
                days=240  # max holiday length is 240 days
            )
            if self.preset_mode == PRESET_BOOST:
                await self._client.set_module_boost(self._zone, self._module, 0)

            # target_temperature is the new temperature when holiday mode ends
            await self._client.set_module_holiday_mode(
                self._zone, self._module, holiday_date, self.target_temperature
            )
        elif preset_mode == PRESET_BOOST:
            _LOGGER.debug("Activate Boost")
            if self.preset_mode == PRESET_AWAY:
                await self._client.disable_module_holiday_mode(
                    self._zone, self._module
                )

            boost_timer = 95  # 95 minutes is the max boost value
            await self._client.set_module_boost(self._zone, self._module, boost_timer)
        elif preset_mode == PRESET_HOME:
            _LOGGER.debug("Go back to normal Mode")
            if self.preset_mode == PRESET_BOOST:
                _LOGGER.debug("Disable Boost mode")
                await self._client.set_module_boost(self._zone, self._module, 0)
            elif self.preset_mode == PRESET_AWAY:
                _LOGGER.debug("Disable Holiday mode")
                await self._client.disable_module_holiday_mode(
                    self._zone, self._module
                )

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        _LOGGER.debug("Set %s heat mode %s", self.entity_id, hvac_mode)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        if self.current_temperature is None or self.target_temperature is None:
            return None
        if self.current_temperature < self.target_temperature:
            return HVACAction.HEATING
        return HVACAction.IDLE

    async def set_window_open_detection(
        self, window_open_detection: bool
    ) -> None:
        """Enable or Disable Window Open Detection."""
        _LOGGER.debug(
            "Set %s Window Open Detection %s", self.name, window_open_detection
        )
        if window_open_detection:
            await self._client.enable_module_window_open_detection(
                zone=self._zone, module=self._module
            )
        else:
            await self._client.disable_module_window_open_detection(
                zone=self._zone, module=self._module
            )

        self._window_open_detection = window_open_detection
        await self.async_update_ha_state()

    async def set_anti_freeze_temperature(self, anti_freeze_temperature: int) -> None:
        """Update Anti Freeze Temperature."""
        _LOGGER.debug(
            "Set %s Anti Freeze Temperature %s", self.name, anti_freeze_temperature
        )

        float_anti_freeze_temperature = float(anti_freeze_temperature)

        await self._client.set_module_anti_freeze_temperature(
            zone=self._zone,
            module=self._module,
            temperature=float_anti_freeze_temperature,
        )

        self._anti_freeze_temperature = float_anti_freeze_temperature
        await self.async_update_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "window_open_detection": self._window_open_detection,
            "anti_freeze_temperature": self._anti_freeze_temperature,
            "boost_time_left": self._boost_time_left,
            "temperature_offset": self._temperature_offset,
            "zone": self._zone,
            "module": self._module,
            "consecutive_failures": self.coordinator.consecutive_failures,
        }

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device specific attributes."""
        return {
            "identifiers": {(DOMAIN, f"thermotec-aeroflow_{self._identifier}")},
            "name": self.name,
            "manufacturer": MANUFACTURER,
            "sw_version": self._sw_version,
            "suggested_area": f"Zone {self._zone}",
        }
