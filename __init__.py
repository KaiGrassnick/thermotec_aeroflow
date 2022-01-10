"""The Thermotec AeroFlow integration."""
import logging

from thermotecaeroflowflexismart.client import Client

from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["climate"]

SERVICE_UPDATE_DATE_TIME = "update_date_time"
SERVICE_UPDATE_WINDOW_OPEN_DETECTION = "update_window_open_detection"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Thermotec AeroFlow from a config entry."""
    _LOGGER.debug("Setting up Thermotec AeroFlow component")

    client = Client(entry.data[CONF_HOST], entry.data[CONF_PORT])

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = client

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


class ThermotecAeroflowEntity(Entity):
    """Representation of a Thermotec Aeroflow heater."""

    _attr_available: bool = False

    def __init__(
        self, client: Client, entity_type: str, zone: int, module: int, identifier: str
    ):
        """Initialize the entity."""
        _LOGGER.debug("New Entity for Zone: %s, Module: %s", zone, module)

        self._client: Client = client
        self._zone: int = zone
        self._module: int = module
        self._identifier: str = identifier
        self._entity_type: str = entity_type

    async def async_update(self, **kwargs):
        """Pull the latest data from Client."""
        try:
            await self._update_status()
            self._attr_available = True
            _LOGGER.debug(
                "Status updated for Zone: %s, Module: %s", self._zone, self._module
            )
        except Exception as err:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            _LOGGER.warning(
                "Connection failed for Zone: %s, Module: %s. Message: %s",
                self._zone,
                self._module,
                message,
            )
            self._attr_available = False

    async def _update_status(self):
        _LOGGER.warning(
            "Update Status for Zone: %s, Module: %s was not implemented",
            self._zone,
            self._module,
        )

    @property
    def name(self):
        """Return the name of the Heater."""
        return f"Thermotec AeroFlow® - {self._entity_type}"

    @property
    def unique_id(self):
        """Return the heater's unique id."""
        return f"thermotec-aeroflow_{self._identifier}_{self._entity_type}"
