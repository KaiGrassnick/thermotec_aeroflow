# Thermotec AeroFlow API Reference

This document provides a comprehensive reference for the `thermotecaeroflowflexismart` Python library API, as used by this Home Assistant integration.

**Library Repository**: https://github.com/KaiGrassnick/py-thermotec-aeroflow-flexismart

## Table of Contents

1. [Client Initialization](#client-initialization)
2. [Gateway Information](#gateway-information)
3. [Zone & Module Discovery](#zone--module-discovery)
4. [Module Data & Control](#module-data--control)
5. [Exceptions](#exceptions)
6. [Data Objects](#data-objects)

---

## Client Initialization

### Creating a Client

```python
from thermotecaeroflowflexismart import Client

# Create client with default port (6653)
client = Client(host="192.168.1.100")

# Create client with custom port
client = Client(host="192.168.1.100", port=6653)
```

### Checking Connectivity

```python
is_online: bool = await client.ping()
```

**Returns**: `bool` - True if gateway is reachable, False otherwise

---

## Gateway Information

### Get Gateway Metadata

```python
gateway_data = await client.get_gateway_data()
```

**Returns**: `GatewayData` object

**Available Methods**:
```python
gateway_data.get_firmware() -> str      # Firmware version (e.g., "1.2.3")
gateway_data.get_installation_id() -> str  # Installation ID
gateway_data.get_idu() -> str           # IDU identifier
```

### Get Network Configuration

```python
network_config = await client.get_network_configuration()
```

**Returns**: `GatewayNetworkConfiguration` object

**Available Methods**:
```python
network_config.get_ip() -> str                    # Gateway IP (e.g., "192.168.1.100")
network_config.get_port() -> int                  # Gateway port (e.g., 6653)
network_config.get_ip_with_port() -> str         # Combined "IP:PORT"
network_config.get_gateway() -> str               # Network gateway IP
network_config.get_subnet_mask() -> str          # Subnet mask (e.g., "255.255.255.0")
network_config.get_registration_server_ip() -> str
network_config.get_registration_server_port() -> int
network_config.get_registration_server_ip_with_port() -> str
```

### Get Gateway Date/Time

```python
date_time = await client.get_date_time()
```

**Returns**: `GatewayDateTime` object

**Available Methods**:
```python
date_time.get_date() -> str        # Date as "DD.MM.YYYY"
date_time.get_time() -> str        # Time as "HH:MM:SS"
date_time.get_date_time_string() -> str  # Combined "DD.MM.YYYY HH:MM:SS"
date_time.get_ip() -> str          # Gateway IP
date_time.get_id() -> str          # Device ID
```

### Update Gateway Date/Time

```python
# Set to current system time
await client.update_date_time()

# Set to specific datetime
from datetime import datetime
await client.set_date_time(datetime.now())
```

---

## Zone & Module Discovery

### Get Available Zones

```python
zones: list[int] = await client.get_zones()
```

**Returns**: `list[int]` - List of zone IDs (usually [1, 2, 3, ...])

### Get Zones with Module Counts

```python
zone_modules: list[int] = await client.get_zones_with_module_count()
```

**Returns**: `list[int]` - Module count per zone (indexed by position)

**Example**:
```python
zones = [3, 2, 1]
# Means:
#   Zone 1 has 3 modules
#   Zone 2 has 2 modules
#   Zone 3 has 1 module
```

**Note**: The list index represents the zone position (starting at 0), not the zone ID.

---

## Module Data & Control

### Get Module Data

```python
module_data = await client.get_module_data(
    zone=1,
    module=1,
    zones=None  # Optional, provide pre-fetched zones to avoid duplicate request
)
```

**Returns**: `ModuleData` object

**Available Methods**:
```python
# Temperature
module_data.get_current_temperature() -> float
module_data.get_target_temperature() -> float

# Device Identification
module_data.get_device_identifier() -> str     # e.g., "192.168.1.100"
module_data.get_firmware_version() -> str

# Status Checks
module_data.is_boost_active() -> bool
module_data.is_smart_start_enabled() -> bool
module_data.is_window_open_detection_enabled() -> bool

# Boost Information
module_data.get_boost_time_left() -> int       # Minutes
module_data.get_boost_time_left_string() -> str  # e.g., "< 15 min."

# Temperature Settings
module_data.get_temperature_offset() -> float

# Other
module_data.get_language() -> str              # "English" or "Deutsch"
module_data.get_time() -> str                  # "HH:MM:SS"
module_data.get_programming_string() -> str
```

### Get All Module Data (Home Assistant Focused)

```python
ha_module_data = await client.get_module_all_data(
    zone=1,
    module=1,
    zones=None,      # Optional
    extended=True    # Include anti-freeze temp, holiday data, date/time
)
```

**Returns**: `HomeAssistantModuleData` object

**Available Methods**:
```python
ha_module_data.get_zone_id() -> int
ha_module_data.get_module_id() -> int
ha_module_data.get_module_data() -> ModuleData
ha_module_data.get_anti_freeze_temperature() -> float | None
ha_module_data.get_holiday_data() -> HolidayData | None
ha_module_data.get_date_time() -> GatewayDateTime | None
```

### Get All Modules Data at Once

```python
all_modules = await client.get_all_data(
    zones=None,      # Optional
    extended=True    # Include extended data
)
# Returns dict[device_identifier, HomeAssistantModuleData]
# e.g., {"192.168.1.100": HomeAssistantModuleData, ...}
```

---

## Temperature Control

### Get Temperature

```python
# Get zone temperature
temp = await client.get_zone_temperature(zone=1)
# Returns: Temperature object

# Get module temperature
temp = await client.get_module_temperature(zone=1, module=1)
```

**Temperature Object**:
```python
temp.get_current_temperature() -> float
temp.get_target_temperature() -> float
```

### Set Temperature

```python
# Set zone temperature
await client.set_zone_temperature(zone=1, temperature=21.0)

# Set module temperature
await client.set_module_temperature(zone=1, module=1, temperature=21.0)
```

**Range**: Typically 5°C to 30°C

### Temperature Offset

```python
# Get offset
offset = await client.get_zone_temperature_offset(zone=1)
offset = await client.get_module_temperature_offset(zone=1, module=1)

# Set offset
await client.set_zone_temperature_offset(zone=1, temperature=2.0)
await client.set_module_temperature_offset(zone=1, module=1, temperature=2.0)
```

---

## Anti-Freeze Temperature

```python
# Get anti-freeze temperature
temp = await client.get_zone_anti_freeze_temperature(zone=1)
temp = await client.get_module_anti_freeze_temperature(zone=1, module=1)

# Set anti-freeze temperature
await client.set_zone_anti_freeze_temperature(zone=1, temperature=5.0)
await client.set_module_anti_freeze_temperature(zone=1, module=1, temperature=5.0)
```

---

## Boost Control

```python
# Get boost status
boost_time = await client.get_zone_boost(zone=1)  # Returns int (minutes)
boost_time = await client.get_module_boost(zone=1, module=1)

# Set boost (0 to disable)
await client.set_zone_boost(zone=1, time=30)  # 30 minutes
await client.set_module_boost(zone=1, module=1, time=30)
```

**Range**: 0-95 minutes (5-minute increments)

---

## Window Open Detection

```python
# Check if enabled
is_enabled = await client.is_zone_window_open_detection_enabled(zone=1)
is_enabled = await client.is_module_window_open_detection_enabled(zone=1, module=1)

# Set
await client.enable_zone_window_open_detection(zone=1)
await client.disable_zone_window_open_detection(zone=1)
await client.set_zone_window_open_detection(zone=1, value=True)

# Same for modules
await client.enable_module_window_open_detection(zone=1, module=1)
await client.disable_module_window_open_detection(zone=1, module=1)
await client.set_module_window_open_detection(zone=1, module=1, value=True)
```

---

## Smart Start Control

```python
# Check if enabled
is_enabled = await client.is_zone_smart_start_enabled(zone=1)
is_enabled = await client.is_module_smart_start_enabled(zone=1, module=1)

# Set
await client.enable_zone_smart_start(zone=1)
await client.disable_zone_smart_start(zone=1)
await client.set_zone_smart_start(zone=1, value=True)

# Same for modules
await client.enable_module_smart_start(zone=1, module=1)
await client.disable_module_smart_start(zone=1, module=1)
await client.set_module_smart_start(zone=1, module=1, value=True)
```

---

## Holiday Mode

```python
# Get holiday status
holiday_data = await client.get_zone_holiday_mode(zone=1)
holiday_data = await client.get_module_holiday_mode(zone=1, module=1)

# Set holiday mode
from datetime import datetime, timedelta

target_date = datetime.now() + timedelta(days=7)
await client.set_zone_holiday_mode(
    zone=1,
    target_datetime=target_date,
    target_temperature=10.0
)
await client.set_module_holiday_mode(
    zone=1,
    module=1,
    target_datetime=target_date,
    target_temperature=10.0
)

# Disable holiday mode
await client.disable_zone_holiday_mode(zone=1)
await client.disable_module_holiday_mode(zone=1, module=1)
```

**Holiday Data Object**:
```python
holiday_data.get_current_temperature() -> float
holiday_data.get_target_temperature() -> float
holiday_data.get_after_holiday_temperature() -> float
holiday_data.get_days_left() -> int
holiday_data.get_end_time() -> str          # "HH:MM"
holiday_data.is_holiday_mode_active() -> bool
```

---

## Zone Management

```python
# Create new zone
await client.create_zone()

# Delete zone (and all heaters in it)
await client.delete_zone(zone=1)

# Register module in zone
await client.register_module_in_zone(zone=1, timeout=30)
```

---

## Module Restart

```python
# Restart a module
module_data = await client.restart_zone(zone=1)
module_data = await client.restart_module(zone=1, module=1)
```

**Returns**: Updated `ModuleData`

---

## Exceptions

The library defines several exception types:

```python
from thermotecaeroflowflexismart.exception import (
    RequestTimeout,   # Request to gateway timed out
    InvalidResponse,  # Gateway response was malformed or unexpected
    InvalidRequest,   # Request parameters were invalid
)
```

### Exception Handling Example

```python
try:
    zone_data = await client.get_module_data(zone=1, module=1)
except RequestTimeout:
    # Handle timeout (gateway unreachable or slow)
    print("Gateway did not respond in time")
except InvalidResponse:
    # Handle malformed response
    print("Unexpected response from gateway")
except Exception as e:
    # Handle any other error
    print(f"Error: {e}")
```

---

## Data Objects

### ModuleData

Represents the complete state of a single module/heater.

```python
class ModuleData:
    get_current_temperature() -> float
    get_target_temperature() -> float
    get_device_identifier() -> str        # Unique identifier
    get_firmware_version() -> str
    get_time() -> str                     # "HH:MM:SS"
    get_language() -> str
    get_temperature_offset() -> float
    get_boost_time_left() -> int          # Minutes
    get_boost_time_left_string() -> str   # "< 15 min."
    is_boost_active() -> bool
    is_smart_start_enabled() -> bool
    is_window_open_detection_enabled() -> bool
    get_programming_string() -> str
```

### Temperature

Represents temperature readings.

```python
class Temperature:
    get_current_temperature() -> float
    get_target_temperature() -> float
```

### HolidayData

Represents holiday mode status.

```python
class HolidayData:
    get_current_temperature() -> float
    get_target_temperature() -> float
    get_after_holiday_temperature() -> float
    get_days_left() -> int
    get_end_time() -> str                 # "HH:MM"
    get_time() -> str                     # "HH:MM:SS"
    is_holiday_mode_active() -> bool
```

### GatewayData

Represents gateway metadata.

```python
class GatewayData:
    get_firmware() -> str
    get_installation_id() -> str
    get_idu() -> str
```

### GatewayNetworkConfiguration

Represents network settings.

```python
class GatewayNetworkConfiguration:
    get_ip() -> str
    get_port() -> int
    get_ip_with_port() -> str
    get_gateway() -> str
    get_subnet_mask() -> str
    get_registration_server_ip() -> str
    get_registration_server_port() -> int
```

### GatewayDateTime

Represents gateway date/time.

```python
class GatewayDateTime:
    get_date() -> str                     # "DD.MM.YYYY"
    get_time() -> str                     # "HH:MM:SS"
    get_date_time_string() -> str         # "DD.MM.YYYY HH:MM:SS"
    get_ip() -> str
    get_id() -> str
```

### HomeAssistantModuleData

Combines module data with extended information (anti-freeze, holiday, date/time).

```python
class HomeAssistantModuleData:
    get_zone_id() -> int
    get_module_id() -> int
    get_module_data() -> ModuleData
    get_anti_freeze_temperature() -> float | None
    get_holiday_data() -> HolidayData | None
    get_date_time() -> GatewayDateTime | None
```

---

## Best Practices

### 1. Reuse Zones List

Instead of fetching zones every time, pass it to methods:

```python
zones = await client.get_zones_with_module_count()

# Reuse zones in subsequent calls
for zone in range(1, len(zones) + 1):
    temp = await client.get_zone_temperature(zone=zone, zones=zones)
```

### 2. Handle Timeouts Gracefully

```python
try:
    data = await asyncio.wait_for(
        client.get_module_data(zone=1, module=1),
        timeout=20
    )
except asyncio.TimeoutError:
    # Handle timeout
    pass
```

### 3. Use Extended Data When Needed

The `extended` parameter in `get_all_data()` adds extra API calls:

```python
# Fast update (basic data only)
data = await client.get_all_data(extended=False)

# Detailed update (includes anti-freeze, holiday, date/time)
data = await client.get_all_data(extended=True)
```

---

## Version Information

**Library Version**: Check setup.py in the [py-thermotec-aeroflow-flexismart](https://github.com/KaiGrassnick/py-thermotec-aeroflow-flexismart) repository

**API Documentation**: All methods documented in `client.py` of the library

**Last Updated**: 2026-01-08
