# Branch Status

## Master Branch

**Status**: ✅ Clean and stable  
**Last Commit**: Revert changes back to pre-refactor state  
**Current Version**: 0.1.0 (stable)

The master branch has been reverted to the state before the architecture refactor. All refactor commits have been moved to the feature branch.

## Feature Branch

**Branch Name**: `feature/multi-coordinator-refactor`  
**Status**: ✅ Ready for review and testing  
**Base**: master (commit 7b968aae4bb67a75d69d36e8a3c2decbf825e548)  
**Commits**: 9 (including new documentation)

### What's in the Feature Branch

Comprehensive refactor implementing:

1. **Multi-Coordinator Architecture**
   - Zones coordinator (zone list)
   - Gateway coordinator (device info)
   - Device coordinators (per-device data)

2. **Configuration Reconfiguration**
   - Users can adjust settings after setup
   - Existing entity IDs preserved
   - Automatic reload on config change

3. **Gateway Device Entity**
   - Gateway appears as a device in Home Assistant
   - Exposes firmware, model, MAC, IP
   - New `ThermotecGatewayEntity` class

4. **Intelligent Availability Tracking**
   - Mark unavailable after 3 failures (not immediately)
   - Exponential backoff retry (5s → 2min max)
   - Automatic recovery on success
   - Visible failure counter in attributes

5. **Modern Best Practices**
   - Full type hints
   - Comprehensive docstrings
   - Proper async/await patterns
   - Modern Home Assistant patterns

### Files in Feature Branch

**New Files**:
- `coordinator.py` - Multi-coordinator implementation
- `ARCHITECTURE.md` - Technical documentation
- `CHANGELOG_REFACTOR.md` - Detailed changelog
- `REFACTOR_STATUS.md` - Branch status and testing checklist

**Modified Files**:
- `const.py` - New constants for coordinators and retry logic
- `config_flow.py` - Reconfiguration flow support
- `__init__.py` - Multi-coordinator setup and gateway entity
- `climate.py` - Per-device coordinator usage

## How to Use

### To Review the Changes

1. Compare the branches on GitHub: `master...feature/multi-coordinator-refactor`
2. Read the documentation:
   - `REFACTOR_STATUS.md` - Overview and testing checklist
   - `ARCHITECTURE.md` - Technical deep dive
   - `CHANGELOG_REFACTOR.md` - Complete feature list

### To Test the Feature Branch

1. Checkout the feature branch
2. Test in Home Assistant with your actual gateway
3. Verify from the testing checklist in `REFACTOR_STATUS.md`
4. Check the underlying API compatibility (see notes in `REFACTOR_STATUS.md`)

### To Merge to Master

When ready:
```bash
git checkout master
git merge feature/multi-coordinator-refactor
# or create a pull request on GitHub
```

No conflicts expected since master was reverted.

## API Compatibility Note

The refactor assumes the following methods exist in `thermotecaeroflowflexismart.Client`:

- `get_gateway_data()` - Returns object with zone/device info methods
- `get_module_data(zone, module, extended)` - Same as before
- `get_module_count(zone)` - Optional, falls back to 1 if missing

If these differ from the actual API, adjustments may be needed in:
- `coordinator.py` (data fetching)
- `climate.py` (module discovery)

See `REFACTOR_STATUS.md` for more details.

## Key Benefits of the Refactor

✨ **New Capabilities**
- Change configuration without removing integration
- Monitor gateway health as a device
- Better visibility into device availability

🚀 **Improved Reliability**
- Smarter unavailability detection (3 failures threshold)
- Exponential backoff prevents log spam
- Staggered updates prevent UDP collisions

📚 **Better Maintainability**
- Modern code patterns and type hints
- Clear separation of concerns
- Comprehensive documentation
- Foundation for future features

🔄 **100% Backward Compatible**
- Existing entity IDs unchanged
- Automations continue to work
- No manual migration needed

## Next Steps

1. **Review**: Check the code and documentation
2. **Test**: Verify with your actual gateway
3. **Verify API**: Confirm the Client API matches expectations
4. **Provide Feedback**: Report issues or suggestions
5. **Merge**: When all tests pass
6. **Release**: As version 0.2.0

## Questions?

Refer to the documentation in the feature branch:
- `REFACTOR_STATUS.md` - Status and checklist
- `ARCHITECTURE.md` - Technical architecture
- `CHANGELOG_REFACTOR.md` - Complete changelog
- Source docstrings - Implementation details

---

**Master**: Clean and stable  
**Feature Branch**: Ready for review and testing
