"""Data coordinators for Thermotec AeroFlow integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from thermotecaeroflowflexismart.client import Client
from thermotecaeroflowflexismart.exception import RequestTimeout, InvalidResponse

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    REQUEST_TIMEOUT,
    UPDATE_INTERVAL_ZONES,
    UPDATE_INTERVAL_DEVICE,
    MAX_CONSECUTIVE_FAILURES,
    MAX_RETRY_BACKOFF,
    MIN_RETRY_BACKOFF,
)

_LOGGER = logging.getLogger(__name__)


class ThermotecZonesCoordinator(DataUpdateCoordinator):
    """Coordinator for zone data.
    
    This coordinator periodically fetches the list of available zones from
    the gateway and stores them. Other coordinators can use this data to
    determine which zones exist.
    """

    def __init__(self, hass: HomeAssistant, client: Client) -> None:
        """Initialize the zones coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_zones",
            update_method=self._async_update_zones,
            update_interval=UPDATE_INTERVAL_ZONES,
        )
        self._client = client
        self.zones: list[int] = []

    async def _async_update_zones(self) -> list[int]:
        """Fetch available zones from the gateway."""
        try:
            # Fetch gateway data to get zones
            async with asyncio.timeout(REQUEST_TIMEOUT):
                gateway_data = await self._client.get_gateway_data()
                # Extract zones from gateway data
                # This assumes the client exposes a method to get zones
                zones = gateway_data.get_zones()
                self.zones = zones
                _LOGGER.debug("Updated zones: %s", zones)
                return zones
        except RequestTimeout as err:
            _LOGGER.error("Timeout fetching zones from Thermotec API: %s", err)
            raise UpdateFailed(f"Timeout fetching zones: {err}") from err
        except InvalidResponse as err:
            _LOGGER.error("Invalid response fetching zones from Thermotec API: %s", err)
            raise UpdateFailed(f"Invalid response fetching zones: {err}") from err
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Unexpected error fetching zones: %s", err)
            raise UpdateFailed(f"Unexpected error fetching zones: {err}") from err


class ThermotecGatewayCoordinator(DataUpdateCoordinator):
    """Coordinator for gateway/hub device data.
    
    Fetches information about the gateway itself (firmware, device info, etc.)
    """

    def __init__(self, hass: HomeAssistant, client: Client) -> None:
        """Initialize the gateway coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_gateway",
            update_method=self._async_update_gateway,
            update_interval=UPDATE_INTERVAL_DEVICE,
        )
        self._client = client

    async def _async_update_gateway(self) -> dict[str, Any]:
        """Fetch gateway information."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                gateway_data = await self._client.get_gateway_data()
                data = {
                    "fw_version": gateway_data.get_firmware_version(),
                    "model": gateway_data.get_model(),
                    "device_name": gateway_data.get_device_name(),
                    "mac_address": gateway_data.get_mac_address(),
                    "ip_address": gateway_data.get_ip_address(),
                }
                _LOGGER.debug("Updated gateway data: %s", data)
                return data
        except RequestTimeout as err:
            _LOGGER.error("Timeout fetching gateway data from Thermotec API: %s", err)
            raise UpdateFailed(f"Timeout fetching gateway data: {err}") from err
        except InvalidResponse as err:
            _LOGGER.error(
                "Invalid response fetching gateway data from Thermotec API: %s", err
            )
            raise UpdateFailed(f"Invalid response fetching gateway data: {err}") from err
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Unexpected error fetching gateway data: %s", err)
            raise UpdateFailed(f"Unexpected error fetching gateway data: {err}") from err


class ThermotecDeviceCoordinator(DataUpdateCoordinator):
    """Coordinator for individual device/module data.
    
    Fetches data for a specific zone/module combination with exponential
    backoff retry logic and availability tracking.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
        zone: int,
        module: int,
        extended_data: bool = True,
    ) -> None:
        """Initialize the device coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_device_{zone}_{module}",
            update_method=self._async_update_device,
            update_interval=UPDATE_INTERVAL_DEVICE,
        )
        self._client = client
        self._zone = zone
        self._module = module
        self._extended_data = extended_data
        self._consecutive_failures = 0
        self._last_success_update = None

    async def _async_update_device(self) -> dict[str, Any]:
        """Fetch device data with error handling and retry logic."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                # Fetch data for specific zone/module
                module_data = await self._client.get_module_data(
                    zone=self._zone,
                    module=self._module,
                    extended=self._extended_data,
                )
                
                # Reset failure counter on success
                self._consecutive_failures = 0
                self._last_success_update = module_data
                
                _LOGGER.debug(
                    "Updated device data for zone=%s, module=%s",
                    self._zone,
                    self._module,
                )
                return module_data
                
        except RequestTimeout as err:
            self._handle_update_failure(
                f"Timeout fetching device data (zone={self._zone}, module={self._module}): {err}"
            )
        except InvalidResponse as err:
            self._handle_update_failure(
                f"Invalid response from device (zone={self._zone}, module={self._module}): {err}"
            )
        except Exception as err:  # pylint: disable=broad-except
            self._handle_update_failure(
                f"Unexpected error fetching device data (zone={self._zone}, module={self._module}): {err}"
            )

    def _handle_update_failure(self, error_message: str) -> None:
        """Handle update failure with exponential backoff logic."""
        self._consecutive_failures += 1
        _LOGGER.warning(
            "%s (failure %d/%d)",
            error_message,
            self._consecutive_failures,
            MAX_CONSECUTIVE_FAILURES,
        )

        # If we've reached max consecutive failures, implement exponential backoff
        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            backoff_factor = min(
                2 ** (self._consecutive_failures - MAX_CONSECUTIVE_FAILURES),
                int(MAX_RETRY_BACKOFF.total_seconds())
                / int(MIN_RETRY_BACKOFF.total_seconds()),
            )
            backoff_time = min(
                MIN_RETRY_BACKOFF * backoff_factor,
                MAX_RETRY_BACKOFF,
            )
            _LOGGER.warning(
                "Device (zone=%s, module=%s) marked unavailable. "
                "Will retry in %s. (attempt %d)",
                self._zone,
                self._module,
                backoff_time,
                self._consecutive_failures,
            )
            self.update_interval = backoff_time
        
        raise UpdateFailed(error_message)

    def mark_available(self) -> None:
        """Mark device as available and reset retry interval."""
        if self._consecutive_failures > 0:
            _LOGGER.info(
                "Device (zone=%s, module=%s) is available again",
                self._zone,
                self._module,
            )
            self._consecutive_failures = 0
            self.update_interval = UPDATE_INTERVAL_DEVICE

    @property
    def is_available(self) -> bool:
        """Return whether the device is currently available."""
        return self._consecutive_failures < MAX_CONSECUTIVE_FAILURES

    @property
    def consecutive_failures(self) -> int:
        """Return the number of consecutive failures."""
        return self._consecutive_failures
