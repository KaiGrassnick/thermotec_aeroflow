"""The Thermotec AeroFlow integration."""
from __future__ import annotations

import logging

from thermotecaeroflowflexismart.client import Client

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import (
    ThermotecZonesCoordinator,
    ThermotecGatewayCoordinator,
    ThermotecDeviceCoordinator,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["climate"]

SERVICE_UPDATE_DATE_TIME = "update_date_time"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Thermotec AeroFlow from a config entry."""
    _LOGGER.debug("Setting up Thermotec AeroFlow component")

    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    extended_data = entry.data.get("extended_data", True)

    client = Client(host, port)

    # Initialize coordinators
    zones_coordinator = ThermotecZonesCoordinator(hass, client)
    gateway_coordinator = ThermotecGatewayCoordinator(hass, client)

    # Perform initial refresh for both coordinators
    try:
        await zones_coordinator.async_config_entry_first_refresh()
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.warning("Failed to fetch zones on startup: %s", err)

    try:
        await gateway_coordinator.async_config_entry_first_refresh()
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.warning("Failed to fetch gateway data on startup: %s", err)

    # Store data in hass
    hass.data.setdefault(DOMAIN, {})
    entry_data = {
        "client": client,
        "zones_coordinator": zones_coordinator,
        "gateway_coordinator": gateway_coordinator,
        "device_coordinators": {},
        "extended_data": extended_data,
    }
    hass.data[DOMAIN][entry.entry_id] = entry_data

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    _register_services(hass, client)

    # Setup update listener for reconfiguration
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Thermotec AeroFlow config updated, reloading entry")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unload Thermotec AeroFlow component")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.services.async_remove(DOMAIN, SERVICE_UPDATE_DATE_TIME)

    return unload_ok


def _register_services(hass: HomeAssistant, client: Client) -> None:
    """Register Thermotec Aeroflow services."""

    async def update_date_time(call):
        _LOGGER.debug("Update the date and time")
        await client.update_date_time()

    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE_DATE_TIME):
        hass.services.async_register(
            DOMAIN, SERVICE_UPDATE_DATE_TIME, update_date_time
        )


class ThermotecAeroflowEntity(CoordinatorEntity, Entity):
    """Base representation of a Thermotec Aeroflow entity."""

    _attr_available: bool = False

    def __init__(
        self,
        coordinator,
        client: Client,
        entity_type: str,
        zone: int | None = None,
        module: int | None = None,
        identifier: str | None = None,
    ):
        """Initialize the entity."""
        super().__init__(coordinator)
        _LOGGER.debug(
            "New Entity: type=%s, zone=%s, module=%s, identifier=%s",
            entity_type,
            zone,
            module,
            identifier,
        )

        self._client: Client = client
        self._zone: int | None = zone
        self._module: int | None = module
        self._identifier: str | None = identifier
        self._entity_type: str = entity_type

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        if self._identifier:
            return f"Thermotec AeroFlow - {self._entity_type} - {self._identifier}"
        return f"Thermotec AeroFlow - {self._entity_type}"

    @property
    def unique_id(self) -> str:
        """Return the entity's unique id."""
        if self._identifier:
            return f"thermotec-aeroflow_{self._entity_type}_{self._identifier}"
        return f"thermotec-aeroflow_{self._entity_type}_gateway"


class ThermotecGatewayEntity(CoordinatorEntity, Entity):
    """Representation of the Thermotec Aeroflow gateway device."""

    _attr_available: bool = False

    def __init__(self, coordinator: ThermotecGatewayCoordinator, client: Client):
        """Initialize the gateway entity."""
        super().__init__(coordinator)
        self._client = client
        self._attr_available = False

    @property
    def name(self) -> str:
        """Return the name of the gateway."""
        return "Thermotec AeroFlow Gateway"

    @property
    def unique_id(self) -> str:
        """Return the gateway's unique id."""
        return "thermotec-aeroflow_gateway"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, "thermotec-aeroflow_gateway")},
            name="Thermotec AeroFlow Gateway",
            manufacturer=MANUFACTURER,
            model=data.get("model", "FlexiSmart Gateway"),
            sw_version=data.get("fw_version", "Unknown"),
            hw_version=data.get("mac_address", "Unknown"),
        )
