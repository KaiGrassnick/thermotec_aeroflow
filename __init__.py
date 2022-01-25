"""The Thermotec AeroFlow integration."""
import logging

import async_timeout
from datetime import timedelta
from thermotecaeroflowflexismart.client import Client
from thermotecaeroflowflexismart.exception import RequestTimeout, InvalidResponse

from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from .const import DOMAIN
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["climate"]

SERVICE_UPDATE_DATE_TIME = "update_date_time"

REGULAR_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Thermotec AeroFlow from a config entry."""
    _LOGGER.debug("Setting up Thermotec AeroFlow component")

    client = Client(entry.data[CONF_HOST], entry.data[CONF_PORT])

    async def async_update_data():
        try:
            async with async_timeout.timeout(20):
                return await client.get_all_data()
        except RequestTimeout as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except InvalidResponse as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=REGULAR_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"client": client, "coordinator": coordinator}

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    _register_services(hass, client)

    return True


@core.callback
def _register_services(hass, client):
    """Register Thermotec Aeroflow services."""

    async def update_date_time(call):
        _LOGGER.debug("Update the date and time")
        await client.update_date_time()

    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE_DATE_TIME):
        hass.services.async_register(DOMAIN, SERVICE_UPDATE_DATE_TIME, update_date_time)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("UnloadThermotec AeroFlow component")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.services.async_remove(DOMAIN, SERVICE_UPDATE_DATE_TIME)

    return unload_ok


class ThermotecAeroflowEntity(CoordinatorEntity, Entity):
    """Representation of a Thermotec Aeroflow heater."""

    _attr_available: bool = False

    def __init__(
            self, coordinator: DataUpdateCoordinator, client: Client, entity_type: str, zone: int, module: int,
            identifier: str):
        """Initialize the entity."""
        super().__init__(coordinator)
        _LOGGER.debug("New Entity for Zone: %s, Module: %s", zone, module)

        self._client: Client = client
        self._zone: int = zone
        self._module: int = module
        self._identifier: str = identifier
        self._entity_type: str = entity_type

    @property
    def name(self):
        """Return the name of the Heater."""
        return f"Thermotec AeroFlow - {self._entity_type} - {self._identifier}"

    @property
    def unique_id(self):
        """Return the heater's unique id."""
        return f"thermotec-aeroflow_{self._entity_type}_{self._identifier}"
