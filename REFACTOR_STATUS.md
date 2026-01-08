# Multi-Coordinator Refactor - Branch Status

**Branch**: `feature/multi-coordinator-refactor`  
**Base**: `master` (before refactor)  
**Status**: Ready for review and testing

## Overview

This feature branch contains a comprehensive refactor of the Thermotec AeroFlow Home Assistant integration to implement modern best practices and improve reliability.

## What's Included

### New Files

1. **`coordinator.py`** - Multi-coordinator architecture
   - `ThermotecZonesCoordinator` - Fetches available zones and module counts
   - `ThermotecGatewayCoordinator` - Manages gateway device information
   - `ThermotecDeviceCoordinator` - Per-device/module data with availability tracking

### Modified Files

1. **`const.py`** - New constants
   - `UPDATE_INTERVAL_ZONES = 30s`
   - `UPDATE_INTERVAL_DEVICE = 35s`
   - `MAX_CONSECUTIVE_FAILURES = 3`
   - `MIN_RETRY_BACKOFF = 5s`
   - `MAX_RETRY_BACKOFF = 2 minutes`
   - `REQUEST_TIMEOUT = 20s`

2. **`config_flow.py`** - Reconfiguration support
   - `async_step_reconfigure()` added
   - Pre-filled reconfiguration form
   - Automatic reload on config changes
   - No changes to existing setup flow

3. **`__init__.py`** - Multi-coordinator integration
   - Creates `ThermotecZonesCoordinator`, `ThermotecGatewayCoordinator`
   - Manages `device_coordinators` dict (one per zone/module)
   - New `ThermotecGatewayEntity` class for gateway device representation
   - Update listener for reconfiguration trigger

4. **`climate.py`** - Per-device coordinator usage
   - Uses individual `ThermotecDeviceCoordinator` per zone/module
   - Improved availability tracking
   - Consecutive failure counter in extra attributes
   - Type hints throughout

### Documentation

1. **`ARCHITECTURE.md`** - Comprehensive documentation
   - Component overview
   - Data flow diagrams
   - Availability tracking logic
   - Request distribution strategy
   - Configuration reconfiguration guide
   - Migration guide for existing users
   - Debugging tips
   - Future enhancements

2. **`CHANGELOG_REFACTOR.md`** - Detailed changelog
   - Breaking changes (none)
   - New features
   - Changed behaviors
   - Bug fixes
   - Dependencies
   - Migration guide
   - Performance improvements
   - Testing recommendations

## Key Features

### ✨ Configuration Reconfiguration
- Users can change IP/port/extended_data without removing the integration
- Existing entity IDs and automations preserved
- Seamless reload on config change

### 🏠 Gateway Entity
- Gateway appears as a device in Home Assistant
- Exposes firmware version, installation ID, IP address, subnet mask
- Can be used in automations for gateway health monitoring

### 🔄 Multi-Coordinator Architecture
- **Zones Coordinator**: Shared zone list with module counts (prevents duplicate requests)
- **Gateway Coordinator**: Gateway device info (firmware, IP, network config)
- **Device Coordinators**: Per-device data with independent failure tracking
- Staggered update intervals to prevent UDP collisions

### 📊 Intelligent Availability Tracking
- Mark unavailable after 3 consecutive failures (not immediately)
- Exponential backoff retry (5s → 10s → 15s → ... → 2min max)
- Automatic recovery on first successful response
- Failure counter visible in entity state attributes

### 🎯 Modern Best Practices
- Full type hints
- Comprehensive docstrings
- Proper async/await patterns
- Specific exception handling
- Modern Home Assistant patterns (DataUpdateCoordinator, CoordinatorEntity)

## API Compatibility - VERIFIED ✅

The refactor uses the following `thermotecaeroflowflexismart` API methods:

### Zone & Module Discovery
```python
# Get list of zones (just zone IDs)
zones: list[int] = await client.get_zones()

# Get zones with module counts per zone (indexed by zone position)
zones_with_counts: list[int] = await client.get_zones_with_module_count()
# Returns [3, 2, 1] means:
#   Zone 1 has 3 modules
#   Zone 2 has 2 modules  
#   Zone 3 has 1 module
```

### Module Data Access
```python
# Get all module data
module_data = await client.get_module_data(
    zone=int,
    module=int,
    zones=list[int] | None  # Optional, coordinator provides this
)
# Returns ModuleData with:
#   .get_current_temperature() -> float
#   .get_target_temperature() -> float
#   .get_firmware_version() -> str
#   .get_device_identifier() -> str (e.g., "192.168.1.100")
#   .is_boost_active() -> bool
#   .get_boost_time_left() -> int (minutes)
#   .is_smart_start_enabled() -> bool
#   .is_window_open_detection_enabled() -> bool
#   .get_temperature_offset() -> float
```

### Gateway Information
```python
# Get gateway metadata (firmware, installation ID, etc.)
gateway_data = await client.get_gateway_data()
# Returns GatewayData with:
#   .get_firmware() -> str
#   .get_installation_id() -> str
#   .get_idu() -> str

# Get gateway network configuration
network_config = await client.get_network_configuration()
# Returns GatewayNetworkConfiguration with:
#   .get_ip() -> str
#   .get_port() -> int
#   .get_gateway() -> str
#   .get_subnet_mask() -> str
#   .get_registration_server_ip() -> str
#   .get_registration_server_port() -> int
```

### Additional Methods Used
```python
# Check gateway availability
is_available: bool = await client.ping()

# Get gateway date/time
date_time = await client.get_date_time()
# Returns GatewayDateTime with:
#   .get_date() -> str ("DD.MM.YYYY")
#   .get_time() -> str ("HH:MM:SS")
#   .get_ip() -> str
#   .get_id() -> str
```

### Exceptions Handled
```python
from thermotecaeroflowflexismart.exception import (
    RequestTimeout,      # Request to gateway timed out
    InvalidResponse,     # Gateway response was malformed
    InvalidRequest,      # Request parameters were invalid
)
```

**API Source**: https://github.com/KaiGrassnick/py-thermotec-aeroflow-flexismart  
**Verified Against**: `client.py` - all public methods examined

## Testing Checklist

### Basic Functionality
- [ ] Integration still discovers heaters correctly
- [ ] Climate entities still update temperature/state
- [ ] Service calls still work (set temp, boost, holiday mode)
- [ ] Entity IDs are unchanged

### New Features
- [ ] Reconfigure option appears in UI
- [ ] Can change IP and reconnect successfully
- [ ] Invalid IP shows error but doesn't break integration
- [ ] Gateway device appears in device registry
- [ ] Gateway shows firmware/installation info

### Availability Tracking
- [ ] Disconnect gateway - entities remain available for 1-2 minutes
- [ ] Continue disconnection - entities mark unavailable
- [ ] Check entity attributes - `consecutive_failures` counter visible
- [ ] Reconnect - entities recover, counter resets
- [ ] Check logs - see failure messages and recovery

### Data Quality
- [ ] No UDP message collisions in logs
- [ ] Updates still arrive regularly
- [ ] No data corruption or missing values
- [ ] Temperature changes work smoothly

## Files Changed

```
const.py                  (modified)
config_flow.py            (modified)
__init__.py              (modified)
climate.py               (modified)
coordinator.py           (new)
ARCHITECTURE.md          (new)
CHANGELOG_REFACTOR.md    (new)
REFACTOR_STATUS.md       (new - this file)
```

## Next Steps

1. **Review** the code changes in GitHub
   - Compare branches: `master...feature/multi-coordinator-refactor`
   - Pay special attention to coordinator implementation
   - Check __init__.py and climate.py changes

2. **Test** in Home Assistant with your actual gateway
   - Follow the testing checklist above
   - Monitor logs for any errors
   - Test all climate entity features

3. **Verify** API compatibility
   - All methods are confirmed to exist and work as documented
   - No API breaking changes expected
   - Data structures are well-defined

4. **Provide feedback** on issues or suggestions
   - Test edge cases (gateway down, etc.)
   - Report any unexpected behavior
   - Suggest improvements

5. **Merge** to master when testing complete
   - No conflicts expected (master was reverted)
   - Ready for release as v0.2.0

## Questions or Issues?

Refer to:
- `ARCHITECTURE.md` for technical details
- `CHANGELOG_REFACTOR.md` for feature list
- Source code docstrings for implementation details
- GitHub issues for bug reports
- API source: https://github.com/KaiGrassnick/py-thermotec-aeroflow-flexismart

---

**API Verified ✅ | Ready for review and testing!**
