# Thermotec AeroFlow Integration Architecture

This document describes the refactored architecture of the Thermotec AeroFlow Home Assistant integration, with a focus on the new multi-coordinator system, gateway entity support, and reconfiguration capabilities.

## Overview

The integration has been modernized to follow current Home Assistant best practices and to provide a more robust, scalable architecture for managing Thermotec AeroFlow devices.

### Key Features

1. **Multi-Coordinator Architecture** - Separate coordinators for different data types
2. **Gateway Device Entity** - The gateway/hub now appears as a device in Home Assistant
3. **Configuration Reconfiguration** - Users can adjust settings after initial setup without recreating the integration
4. **Improved Availability Tracking** - Smart availability detection with exponential backoff retry logic
5. **Modern Home Assistant Patterns** - Follows latest HA development guidelines (2024+)

## Architecture Components

### 1. Zones Coordinator (`ThermotecZonesCoordinator`)

**Purpose**: Periodically fetches the list of available zones from the gateway

**Characteristics**:
- Updates every 30 seconds (configurable via `UPDATE_INTERVAL_ZONES`)
- Stores zone list in memory: `coordinator.zones`
- Acts as the source of truth for available zones
- Other coordinators can reference this data without duplicate requests

**Update Interval**: 30 seconds

**Data Structure**:
```python
coordinator.data = [1, 2, 6, 4]  # List of available zone IDs
coordinator.zones = [1, 2, 6, 4]  # Alias for easier access
```

### 2. Gateway Coordinator (`ThermotecGatewayCoordinator`)

**Purpose**: Fetches and maintains gateway/hub device information

**Characteristics**:
- Updates every 35 seconds (configurable via `UPDATE_INTERVAL_DEVICE`)
- Provides device information for the gateway entity
- Includes firmware version, model, MAC address, IP address
- Single coordinator for the entire gateway (not zone-specific)

**Update Interval**: 35 seconds (slightly offset from zones to distribute load)

**Data Structure**:
```python
coordinator.data = {
    "fw_version": "1.2.3",
    "model": "FlexiSmart Gateway",
    "device_name": "Aeroflow Gateway",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "ip_address": "192.168.1.100"
}
```

### 3. Device Coordinator (`ThermotecDeviceCoordinator`)

**Purpose**: Fetches data for individual zone/module combinations

**Characteristics**:
- One coordinator per zone/module pair
- Updates every 35 seconds (with jitter to avoid simultaneous requests)
- **Smart Availability Tracking**: Marks devices unavailable after 3 consecutive failures
- **Exponential Backoff**: Increases retry interval exponentially up to 2 minutes
- Resets backoff and marks device available again on first successful update
- Stores consecutive failure count for monitoring

**Update Interval**: 35 seconds (normal) → exponential backoff up to 2 minutes (after 3 failures)

**Availability Logic**:
```
Success → consecutive_failures = 0, update_interval = 35s

Failure 1 → consecutive_failures = 1, update_interval = 35s
Failure 2 → consecutive_failures = 2, update_interval = 35s
Failure 3+ → consecutive_failures = 3+, update_interval = exponential backoff
            Max backoff = 2 minutes
            
Success (after failures) → consecutive_failures = 0, update_interval = 35s
```

**Data Structure**:
```python
coordinator.data = ModuleData(...)  # Module-specific data
coordinator.consecutive_failures = 0-3+  # Failure counter
coordinator.is_available  # Property: True if failures < MAX_CONSECUTIVE_FAILURES
```

## Data Flow

```
Setup Entry
    ↓
    ├─→ Create Client
    ├─→ Create ZonesCoordinator → Fetch zone list [1,2,6,4]
    ├─→ Create GatewayCoordinator → Fetch gateway info
    └─→ Create DeviceCoordinator per zone/module → Fetch module data

Continuous Updates
    ↓
    ├─→ ZonesCoordinator.update() → List of zones
    ├─→ GatewayCoordinator.update() → Gateway device info
    └─→ DeviceCoordinator[].update() → Individual module data
            (with staggered timing to avoid UDP message collision)

Entity Updates
    ↓
    └─→ Climate entities listen to DeviceCoordinator
        └─→ Listen to _handle_coordinator_update()
            └─→ Update entity state
```

## Configuration Reconfiguration

Users can now adjust the integration configuration after initial setup:

**Settings that can be changed**:
- `host` - Gateway IP address
- `port` - Gateway port (default: 6653)
- `extended_data` - Enable/disable extended data fetching

**How it works**:
1. User goes to "Settings" → "Devices & Services" → "Thermotec AeroFlow"
2. Clicks the three dots menu and selects "Reconfigure"
3. Form appears pre-filled with current values
4. User makes changes and submits
5. Integration automatically reloads with new settings
6. Existing entities and automations remain untouched

**Implementation Details** (in `config_flow.py`):
```python
async def async_step_reconfigure(...):
    # Validates new connection
    # Updates config entry data
    # Triggers async_reload to apply changes
    # Existing entity IDs remain the same
```

## Gateway Entity

The gateway now appears as a device in Home Assistant:

**Device Info**:
- **Name**: Thermotec AeroFlow Gateway
- **Model**: FlexiSmart Gateway (from API)
- **Firmware**: Version from gateway
- **Manufacturer**: Thermotec AG
- **MAC Address**: Shown as hardware version

**Entity Created**:
- `binary_sensor.thermotec_aeroflow_gateway` (availability sensor)

**Accessible via**:
- Device card in Home Assistant UI
- Entity card for gateway availability
- Automations and scripts using gateway availability

## Request Distribution and Load Balancing

To prevent UDP message collisions and overwhelm the gateway:

### Update Interval Offsets
```
ZonesCoordinator    → Updates at: 0s, 30s, 60s, ...
GatewayCoordinator  → Updates at: 5s, 40s, 75s, ...
DeviceCoordinator 1 → Updates at: 10s, 45s, 80s, ...
DeviceCoordinator 2 → Updates at: 15s, 50s, 85s, ...
DeviceCoordinator 3 → Updates at: 20s, 55s, 90s, ...
...
```

### Implementation
- Each device coordinator can add a small random jitter (0-5 seconds)
- Staggering reduces concurrent requests
- Gateway can handle requests sequentially without UDP collisions

## Availability Tracking

### States

1. **Available**
   - Device is responding to requests
   - `consecutive_failures < 3`
   - Updates normally every 35 seconds
   - Entity is marked as available

2. **Temporarily Unavailable** (Soft Unavailable)
   - Device hasn't responded for 1-2 consecutive attempts
   - Still updates at normal interval
   - Entity remains available (assumption: transient issue)

3. **Unavailable** (Hard Unavailable)
   - Device hasn't responded for 3+ consecutive attempts
   - Update interval increases (exponential backoff)
   - Entity marked as unavailable
   - Entity card shows unavailable in UI

4. **Recovery**
   - Device responds after being unavailable
   - `consecutive_failures` resets to 0
   - Update interval resets to normal (35 seconds)
   - Entity marked as available again

### Exponential Backoff Formula

```python
backoff_factor = min(
    2^(consecutive_failures - 3),
    MAX_RETRY_BACKOFF / MIN_RETRY_BACKOFF
)
backoff_time = min(
    MIN_RETRY_BACKOFF * backoff_factor,
    MAX_RETRY_BACKOFF
)
```

**Examples**:
- Failure 3: backoff = 5s * 2^0 = 5s
- Failure 4: backoff = 5s * 2^1 = 10s
- Failure 5: backoff = 5s * 2^2 = 20s
- Failure 6: backoff = 5s * 2^3 = 40s
- Failure 7: backoff = 5s * 2^4 = 80s
- Failure 8: backoff = 5s * 2^5 = 120s (capped at MAX_RETRY_BACKOFF = 120s)
- Failure 9+: backoff = 120s (max)

**Configuration** (in `const.py`):
```python
MAX_CONSECUTIVE_FAILURES = 3
MIN_RETRY_BACKOFF = timedelta(seconds=5)
MAX_RETRY_BACKOFF = timedelta(minutes=2)
```

## Modern Home Assistant Best Practices Implemented

### 1. Type Hints
- All functions have proper type hints
- Return types are specified
- Improves IDE support and catches errors early

### 2. Docstrings
- Comprehensive docstrings for all classes and methods
- Explains purpose, parameters, and return values

### 3. Async/Await
- All I/O operations use async/await pattern
- Uses `asyncio.timeout()` instead of deprecated `async_timeout`
- Proper error handling with context managers

### 4. Error Handling
- Specific exception types caught and handled
- Logging at appropriate levels (debug, warning, error)
- Graceful degradation when services unavailable

### 5. Coordinator Pattern
- Uses `DataUpdateCoordinator` for all data fetching
- Proper `UpdateFailed` exceptions
- Shared data across multiple entities

### 6. Entity Pattern
- `CoordinatorEntity` for automatic state updates
- `DeviceInfo` for device grouping
- Proper `unique_id` for entity tracking
- `extra_state_attributes` for additional data

### 7. Configuration Flow
- Two-step flow: user input + reconfiguration
- Pre-filled reconfiguration form
- Validation of connection on every step
- Automatic reload on configuration changes

### 8. Constants
- All magic numbers in `const.py`
- Easy to adjust without code changes
- Clear naming conventions

## Migration Guide for Existing Installations

If upgrading from the old architecture:

### Entity ID Preservation
- Entity IDs remain unchanged
- Existing automations and scripts continue to work
- No manual reconfiguration needed

### New Features to Explore
1. **Reconfigure Option**: Try changing host/port without removing the integration
2. **Gateway Device**: Look for new gateway device in device registry
3. **Availability Tracking**: Monitor device unavailability in entity details
4. **Better Logging**: Check logs for detailed debugging information

## Debugging

### Enable Debug Logging
```yaml
logger:
  logs:
    custom_components.thermotec_aeroflow: debug
    custom_components.thermotec_aeroflow.coordinator: debug
```

### What to Look For
```
DEBUG: New Entity: type=Heater, zone=1, module=1, identifier=zone_1_module_1
DEBUG: Updated device data for zone=1, module=1
WARNING: Device (zone=1, module=1) marked unavailable. Will retry in 5 seconds
INFO: Device (zone=1, module=1) is available again
```

## Future Enhancements

1. **Discovery Protocol**: Auto-discover gateway on local network
2. **Sensor Entities**: Add sensor platform for gateway metrics
3. **Diagnostics**: Implement diagnostic dump for troubleshooting
4. **Options Flow**: Allow users to adjust update intervals via UI
5. **Device Health Dashboard**: Visual representation of device availability
6. **Statistics**: Track uptime and reliability of each device

## Constants Reference

**File**: `const.py`

```python
# Update intervals
UPDATE_INTERVAL_ZONES = timedelta(seconds=30)  # Zone list refresh
UPDATE_INTERVAL_DEVICE = timedelta(seconds=35)  # Device data refresh

# Availability settings
MAX_CONSECUTIVE_FAILURES = 3  # Failures before unavailable
MIN_RETRY_BACKOFF = timedelta(seconds=5)  # Min backoff time
MAX_RETRY_BACKOFF = timedelta(minutes=2)  # Max backoff time

# Request settings
REQUEST_TIMEOUT = 20  # Seconds to wait for gateway response
```

## References

- [Home Assistant Coordinator Documentation](https://developers.home-assistant.io/docs/integration_fetching_data)
- [Entity Architecture](https://developers.home-assistant.io/docs/entity/)
- [Device Registry](https://developers.home-assistant.io/docs/device_registry/)
- [Config Entries](https://developers.home-assistant.io/docs/config_entries/)
