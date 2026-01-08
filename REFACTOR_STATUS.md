# Multi-Coordinator Refactor - Branch Status

**Branch**: `feature/multi-coordinator-refactor`  
**Base**: `master` (before refactor)  
**Status**: Ready for review and testing

## Overview

This feature branch contains a comprehensive refactor of the Thermotec AeroFlow Home Assistant integration to implement modern best practices and improve reliability.

## What's Included

### New Files

1. **`coordinator.py`** - Multi-coordinator architecture
   - `ThermotecZonesCoordinator` - Fetches available zones periodically
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
- Exposes firmware version, model, MAC address, IP address
- Can be used in automations for gateway health monitoring

### 🔄 Multi-Coordinator Architecture
- **Zones Coordinator**: Shared zone list (prevents duplicate requests)
- **Gateway Coordinator**: Gateway device info
- **Device Coordinators**: Per-device data with independent failure tracking
- Staggered update intervals to prevent UDP collisions

### 📊 Intelligent Availability Tracking
- Mark unavailable after 3 consecutive failures (not immediately)
- Exponential backoff retry (5s → 10s → 20s → ... → 2min max)
- Automatic recovery on first successful response
- Failure counter visible in entity state attributes

### 🎯 Modern Best Practices
- Full type hints
- Comprehensive docstrings
- Proper async/await patterns
- Specific exception handling
- Modern Home Assistant patterns (DataUpdateCoordinator, CoordinatorEntity)

## API Compatibility Notes

The refactor assumes the following `thermotecaeroflowflexismart` API:

```python
# Gateway data access
await client.get_gateway_data()  # Returns object with:
  .get_zones()              # List[int] of available zones
  .get_firmware_version()   # str
  .get_model()             # str
  .get_device_name()       # str
  .get_mac_address()       # str
  .get_ip_address()        # str

# Module data access
await client.get_module_data(zone=int, module=int, extended=bool)
  # Returns module data object (same as before)

# Helper method (fallback to 1 if not available)
await client.get_module_count(zone=int)  # Returns int
```

If your API differs, these methods may need adjustment in:
- `coordinator.py` (data fetching)
- `climate.py` (module discovery)

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
- [ ] Gateway shows firmware/model info

### Availability Tracking
- [ ] Disconnect gateway - entities remain available for 1-2 minutes
- [ ] Continue disconnection - entities mark unavailable
- [ ] Check entity attributes - `consecutive_failures` counter visible
- [ ] Reconnect - entities recover, counter resets
- [ ] Check logs - see exponential backoff messages

### Data Quality
- [ ] No UDP message collisions in logs
- [ ] Updates still arrive regularly
- [ ] No data corruption or missing values
- [ ] Temperature changes work smoothly

## Migration Path

For existing users:
1. Update to this branch
2. Integration auto-reloads (no manual action needed)
3. Existing automations continue to work
4. Old entity IDs preserved
5. New features available to use optionally

## Known Limitations

1. **Module discovery** - Currently assumes `client.get_module_count(zone)` exists
   - If not available in your API, will need adjustment
   - Fallback to 1 module per zone currently built-in

2. **Zone discovery** - Requires `get_gateway_data().get_zones()`
   - If API structure differs, coordinators need updates

3. **Coordinator data format** - Assumes module data structure matches `HomeAssistantModuleData`
   - Handles both that type and generic module-like objects

## Next Steps

1. **Review** the code changes in GitHub
2. **Test** in Home Assistant with real gateway
3. **Verify** API compatibility with your `thermotecaeroflowflexismart` package
4. **Provide feedback** on issues or edge cases
5. **Merge** to master when testing complete
6. **Release** as version 0.2.0

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

## Questions or Issues?

Refer to:
- `ARCHITECTURE.md` for technical details
- `CHANGELOG_REFACTOR.md` for feature list
- Source code docstrings for implementation details
- GitHub issues for bug reports

---

**Ready for review and testing!**
