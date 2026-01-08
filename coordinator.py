"""Data update coordinators for Thermotec AeroFlow integration."""
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from thermotecaeroflowflexismart import Client
from thermotecaeroflowflexismart.exception import (
    RequestTimeout,
    InvalidResponse,
)

from .const import (
    DOMAIN,
    UPDATE_INTERVAL_ZONES,
    UPDATE_INTERVAL_DEVICE,
    MAX_CONSECUTIVE_FAILURES,
    MIN_RETRY_BACKOFF,
    MAX_RETRY_BACKOFF,
)

_LOGGER = logging.getLogger(__name__)


class ThermotecZonesCoordinator(DataUpdateCoordinator):
    """Coordinator for fetching available zones from the gateway.
    
    This coordinator is shared across all integrations for the same gateway
    to avoid duplicate zone list requests.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
    ) -> None:
        """Initialize the zones coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Thermotec Zones",
            update_interval=UPDATE_INTERVAL_ZONES,
        )
        self.client = client
        self._data: list[int] = []

    async def _async_update_data(self) -> list[int]:
        """Fetch zones from gateway.
        
        Returns a list where each index represents a zone (starting at 0),
        and the value is the module count for that zone.
        """
        try:
            zones = await self.client.get_zones_with_module_count()
            _LOGGER.debug("Fetched zones: %s", zones)
            self._data = zones
            return zones
        except RequestTimeout as err:
            raise UpdateFailed(f"Request timeout fetching zones: {err}") from err
        except InvalidResponse as err:
            raise UpdateFailed(f"Invalid response fetching zones: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching zones: {err}") from err

    def get_zones(self) -> list[int]:
        """Get the last successfully fetched zones."""
        return self._data


class ThermotecGatewayCoordinator(DataUpdateCoordinator):
    """Coordinator for gateway device information.
    
    Fetches gateway metadata like firmware version, installation ID, etc.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
    ) -> None:
        """Initialize the gateway coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Thermotec Gateway",
            update_interval=UPDATE_INTERVAL_ZONES,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch gateway data and network configuration.
        
        Returns a dictionary with gateway metadata.
        """
        try:
            gateway_data = await self.client.get_gateway_data()
            network_config = await self.client.get_network_configuration()
            
            data = {
                "firmware": gateway_data.get_firmware(),
                "installation_id": gateway_data.get_installation_id(),
                "idu": gateway_data.get_idu(),
                "ip": network_config.get_ip(),
                "port": network_config.get_port(),
                "gateway": network_config.get_gateway(),
                "subnet_mask": network_config.get_subnet_mask(),
            }
            _LOGGER.debug("Fetched gateway data: firmware=%s, ip=%s", 
                         data["firmware"], data["ip"])
            return data
        except RequestTimeout as err:
            raise UpdateFailed(f"Request timeout fetching gateway data: {err}") from err
        except InvalidResponse as err:
            raise UpdateFailed(f"Invalid response fetching gateway data: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching gateway data: {err}") from err


class ThermotecDeviceCoordinator(DataUpdateCoordinator):
    """Coordinator for individual device/module data with availability tracking.
    
    Tracks consecutive failures and implements exponential backoff retry logic.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
        zone: int,
        module: int,
        zones_coordinator: "ThermotecZonesCoordinator",
    ) -> None:
        """Initialize the device coordinator.
        
        Args:
            hass: Home Assistant instance
            client: Thermotec client
            zone: Zone ID (1-indexed)
            module: Module ID (1-indexed)
            zones_coordinator: Shared zones coordinator for getting zone list
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"Thermotec Device Zone {zone} Module {module}",
            update_interval=UPDATE_INTERVAL_DEVICE,
        )
        self.client = client
        self.zone = zone
        self.module = module
        self.zones_coordinator = zones_coordinator
        
        # Availability tracking
        self._consecutive_failures = 0
        self._is_available = True
        self._current_retry_backoff = MIN_RETRY_BACKOFF

    @property
    def available(self) -> bool:
        """Return whether the device is available.
        
        Device is marked unavailable after MAX_CONSECUTIVE_FAILURES failures.
        """
        return self._is_available

    @property
    def consecutive_failures(self) -> int:
        """Return the number of consecutive failures."""
        return self._consecutive_failures

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch module data with availability tracking.
        
        Implements exponential backoff and consecutive failure tracking.
        """
        try:
            zones = self.zones_coordinator.get_zones()
            if not zones:
                # Zones not yet fetched, can't proceed
                raise UpdateFailed("Zones not yet available from zones coordinator")
            
            # Get full module data (includes basic module info)
            module_data = await self.client.get_module_data(
                zone=self.zone,
                module=self.module,
                zones=zones,
            )
            
            # Reset failure tracking on success
            self._consecutive_failures = 0
            self._current_retry_backoff = MIN_RETRY_BACKOFF
            
            if not self._is_available:
                self._is_available = True
                _LOGGER.info(
                    "Device Zone %d Module %d recovered and is now available",
                    self.zone, self.module
                )
            
            # Return the module data as dict for coordinator
            return {
                "zone_id": self.zone,
                "module_id": self.module,
                "module_data": module_data,
                "current_temperature": module_data.get_current_temperature(),
                "target_temperature": module_data.get_target_temperature(),
                "is_boost_active": module_data.is_boost_active(),
                "boost_time_left": module_data.get_boost_time_left(),
                "temperature_offset": module_data.get_temperature_offset(),
                "is_smart_start_enabled": module_data.is_smart_start_enabled(),
                "is_window_open_detection_enabled": module_data.is_window_open_detection_enabled(),
                "firmware_version": module_data.get_firmware_version(),
                "device_identifier": module_data.get_device_identifier(),
            }
        
        except RequestTimeout as err:
            self._consecutive_failures += 1
            _LOGGER.debug(
                "Request timeout for Zone %d Module %d (failure %d/%d): %s",
                self.zone, self.module, self._consecutive_failures,
                MAX_CONSECUTIVE_FAILURES, err
            )
            self._check_availability()
            raise UpdateFailed(
                f"Request timeout for Zone {self.zone} Module {self.module}"
            ) from err
        
        except InvalidResponse as err:
            self._consecutive_failures += 1
            _LOGGER.debug(
                "Invalid response for Zone %d Module %d (failure %d/%d): %s",
                self.zone, self.module, self._consecutive_failures,
                MAX_CONSECUTIVE_FAILURES, err
            )
            self._check_availability()
            raise UpdateFailed(
                f"Invalid response for Zone {self.zone} Module {self.module}"
            ) from err
        
        except Exception as err:
            self._consecutive_failures += 1
            _LOGGER.debug(
                "Unexpected error for Zone %d Module %d (failure %d/%d): %s",
                self.zone, self.module, self._consecutive_failures,
                MAX_CONSECUTIVE_FAILURES, err
            )
            self._check_availability()
            raise UpdateFailed(
                f"Error fetching data for Zone {self.zone} Module {self.module}"
            ) from err

    def _check_availability(self) -> None:
        """Check if device should be marked unavailable.
        
        Marks device unavailable after MAX_CONSECUTIVE_FAILURES failures.
        """
        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES and self._is_available:
            self._is_available = False
            _LOGGER.warning(
                "Device Zone %d Module %d marked unavailable after %d consecutive failures",
                self.zone, self.module, self._consecutive_failures
            )

    async def async_request_refresh(self) -> None:
        """Request a refresh of the data.
        
        Implements exponential backoff for retries.
        """
        # Only apply backoff if we have failures
        if self._consecutive_failures > 0:
            # Calculate backoff: min + (consecutive_failures - 1) * interval
            backoff_seconds = min(
                (self._consecutive_failures - 1) * 5,  # 0, 5, 10, 15, ... seconds
                MAX_RETRY_BACKOFF.total_seconds()
            )
            if backoff_seconds > 0:
                _LOGGER.debug(
                    "Applying exponential backoff of %.0f seconds for Zone %d Module %d",
                    backoff_seconds, self.zone, self.module
                )
        
        await super().async_request_refresh()
