# Changelog - Architecture Refactor

## Version 0.1.0 → 0.2.0 (Major Refactor)

### 🆕 Breaking Changes

None - The refactor maintains backward compatibility with existing configurations and entity IDs.

### ✨ New Features

#### 1. Configuration Reconfiguration Support
- **Feature**: Users can now adjust integration settings after initial setup
- **How to use**: Home Assistant UI → Settings → Devices & Services → Thermotec AeroFlow → Menu → Reconfigure
- **What can be changed**: 
  - Gateway IP address/hostname
  - Gateway port
  - Extended data fetching toggle
- **Benefit**: No need to remove and re-add integration for configuration changes
- **Implementation**: Added `async_step_reconfigure()` in `config_flow.py`

#### 2. Gateway Device Entity
- **Feature**: The gateway/hub now appears as a device in Home Assistant
- **Device Info Includes**:
  - Firmware version
  - Model information
  - MAC address
  - IP address
  - Device name
- **Benefits**:
  - Monitor gateway health and status
  - Unified device management
  - Better organization in Home Assistant
- **Implementation**: New `ThermotecGatewayEntity` and `ThermotecGatewayCoordinator`

#### 3. Multi-Coordinator Architecture
- **Zones Coordinator**: Fetches available zones from gateway
  - Updates every 30 seconds
  - Provides zone list to other coordinators
  - Prevents duplicate zone queries
  
- **Gateway Coordinator**: Fetches gateway device information
  - Updates every 35 seconds
  - Separate from device data (not zone-specific)
  - Powers the new gateway entity
  
- **Device Coordinators**: Individual coordinators per zone/module
  - One coordinator per physical device
  - Distributed update timing to prevent collisions
  - Independent failure tracking and recovery

**Benefits**:
- Cleaner separation of concerns
- Ability to reuse zone data across multiple coordinators
- Independent error handling per device
- Foundation for future expansion (sensors, etc.)

#### 4. Intelligent Availability Tracking
- **Smart Detection**: Devices automatically marked unavailable after 3 consecutive failures
- **Exponential Backoff Retry Logic**:
  - Failure 1-2: Normal polling (35 seconds)
  - Failure 3+: Exponential backoff starting at 5 seconds
  - Maximum backoff: 2 minutes
  - Automatic recovery: Reset on first successful update
  
**Example Scenario**:
```
Time 0:00 - Device offline (failure 1) → Polling continues
Time 0:35 - Device offline (failure 2) → Polling continues
Time 1:10 - Device offline (failure 3) → UNAVAILABLE + Backoff starts
Time 1:15 - Retry with 5s backoff
Time 1:20 - Retry with 10s backoff
Time 1:30 - Retry with 20s backoff
Time 1:50 - Retry with 40s backoff (cumulative ~70s since failure 3)
Time 2:30 - Device comes back online → AVAILABLE + Normal polling resumes
```

**Benefits**:
- Prevents log spam from offline devices
- Reduces unnecessary network traffic
- More realistic representation of device state
- Automatic recovery without manual intervention

#### 5. Modern Home Assistant Best Practices

**Code Quality**:
- Full type hints for all functions
- Comprehensive docstrings
- Proper async/await patterns
- Modern exception handling

**Architecture Patterns**:
- `DataUpdateCoordinator` for all data fetching
- `CoordinatorEntity` for state synchronization
- Proper `DeviceInfo` usage for device grouping
- Modern error handling with `UpdateFailed`

**Configuration Flow**:
- Two-step flow (initial setup + reconfiguration)
- Validation at every step
- Pre-filled reconfiguration form
- Automatic reload on changes

### 📝 Changed

#### `const.py`
**Before**:
```python
UPDATE_INTERVAL_DEVICES = timedelta(seconds=30)
```

**After**:
```python
UPDATE_INTERVAL_ZONES = timedelta(seconds=30)
UPDATE_INTERVAL_DEVICE = timedelta(seconds=35)

MAX_CONSECUTIVE_FAILURES = 3
MAX_RETRY_BACKOFF = timedelta(minutes=2)
MIN_RETRY_BACKOFF = timedelta(seconds=5)
REQUEST_TIMEOUT = 20
```

#### `config_flow.py`
**Before**:
- One-step setup only
- No reconfiguration support

**After**:
- Two-step flow (user input + reconfiguration)
- Reconfiguration form with pre-filled values
- Automatic integration reload on config changes

#### `__init__.py`
**Before**:
- Single coordinator for all data
- No gateway entity

**After**:
- Three coordinators (zones, gateway, devices)
- Gateway entity available
- Better separation of concerns
- Proper update listener for reconfiguration

#### `climate.py`
**Before**:
- Direct usage of single coordinator
- All data fetched together
- Basic availability tracking

**After**:
- Individual device coordinators
- Proper availability tracking with exponential backoff
- Consecutive failure counter in extra attributes
- Better error handling and logging
- Type hints throughout

### 🐛 Bug Fixes

1. **UDP Message Collisions**: Distributed update timing prevents multiple simultaneous requests to gateway
2. **Availability Flickering**: Smart threshold (3 failures) prevents temporary issues from marking device unavailable
3. **Error Recovery**: Exponential backoff prevents log spam from persistently offline devices
4. **Entity ID Instability**: New architecture preserves entity IDs through reconfiguration

### 🧪 Dependencies

**No new external dependencies added**

Refactoring uses only existing Home Assistant and Python standard library:
- `asyncio` - Standard async library with new `asyncio.timeout()` (replaces `async_timeout`)
- `logging` - Standard logging
- `datetime` - Standard timedelta
- `homeassistant.helpers.update_coordinator` - Existing, updated patterns

### 📄 Documentation

New files added:
- **ARCHITECTURE.md** - Comprehensive architecture documentation
  - Component overview
  - Data flow diagrams
  - Availability tracking logic
  - Configuration reconfiguration guide
  - Migration guide
  - Debugging tips

### 🧰 Migration Guide

#### For Existing Users

**No action required!**

- Your integration will continue to work
- Entity IDs remain the same
- Existing automations unchanged
- Existing scripts unchanged

**Optional: Try New Features**

1. **Reconfigure Settings**
   - Go to Settings → Devices & Services
   - Find "Thermotec AeroFlow"
   - Click the three dots and select "Reconfigure"
   - Adjust IP/port as needed

2. **Monitor Gateway**
   - Look for new "Thermotec AeroFlow Gateway" device
   - Check device availability status
   - Monitor gateway health

3. **Debug Availability Issues**
   - Check entity details for "consecutive_failures"
   - Enable debug logging to see retry attempts
   - Review logs for troubleshooting

#### For Developers

If you're using the underlying `thermotecaeroflowflexismart` package:

1. **New coordinator imports**:
   ```python
   from custom_components.thermotec_aeroflow.coordinator import (
       ThermotecZonesCoordinator,
       ThermotecGatewayCoordinator,
       ThermotecDeviceCoordinator,
   )
   ```

2. **Gateway data access**:
   ```python
   gateway_coordinator = hass.data[DOMAIN][entry_id]["gateway_coordinator"]
   gateway_info = gateway_coordinator.data
   ```

3. **Device coordinator access**:
   ```python
   device_coordinator = device_coordinators["zone_1_module_1"]
   is_available = device_coordinator.is_available
   failures = device_coordinator.consecutive_failures
   ```

### 🔒 Performance Improvements

1. **Reduced UDP Collisions**: Staggered update timing
2. **Smarter Retries**: Exponential backoff reduces network traffic
3. **Better Load Distribution**: Multiple coordinators prevent blocking
4. **Efficient Data Reuse**: Zone data cached across coordinators

### 🦹 Testing Recommendations

For users testing the new features:

1. **Reconfiguration Flow**
   - Change gateway IP/port and verify reconnection
   - Test with invalid IP and verify error handling
   - Verify entity IDs remain stable

2. **Availability Tracking**
   - Disconnect gateway and monitor availability state
   - Reconnect and verify recovery
   - Check consecutive_failures counter

3. **Device Health**
   - Monitor gateway device card
   - Check firmware version display
   - Verify device grouping

### 🄀 Constants Changes

| Constant | Old Value | New Value | Purpose |
|----------|-----------|-----------|----------|
| `UPDATE_INTERVAL_DEVICES` | 30s | Removed | Replaced with zone/device specific |
| `UPDATE_INTERVAL_ZONES` | N/A | 30s | Zone list refresh rate |
| `UPDATE_INTERVAL_DEVICE` | N/A | 35s | Device data refresh rate |
| `MAX_CONSECUTIVE_FAILURES` | N/A | 3 | Failures before unavailable |
| `MIN_RETRY_BACKOFF` | N/A | 5s | Minimum backoff time |
| `MAX_RETRY_BACKOFF` | N/A | 2min | Maximum backoff time |
| `REQUEST_TIMEOUT` | N/A | 20s | API request timeout |

### 📥 Next Steps

1. **Testing**: Thoroughly test reconfiguration and availability tracking
2. **Feedback**: Report issues or feature requests
3. **Documentation**: Contribute to documentation improvements
4. **Integration**: Prepare for next minor/major version release

### 🙋 Contributors

- **Refactoring**: Implemented modern architecture and best practices
- **Documentation**: Created ARCHITECTURE.md and CHANGELOG_REFACTOR.md
- **Testing**: Validated backward compatibility

### 🔗 Related Issues

- Users could not adjust configuration without removing integration
- Gateway had no representation in Home Assistant
- Single coordinator caused unnecessary data fetching
- Limited availability tracking for offline devices
- Code patterns from 2022 not aligned with current HA standards

### 🈐 Future Roadmap

- [ ] Sensor platform for gateway metrics
- [ ] Options flow for adjusting update intervals
- [ ] Diagnostic dump for troubleshooting
- [ ] Auto-discovery protocol
- [ ] Device health dashboard
- [ ] Statistics tracking (uptime, reliability)
- [ ] Multi-gateway support

---

**Upgrade Note**: This refactor maintains 100% backward compatibility. No user action required, but new features are available for those who want to use them.
