---
phase: 03-coordinator-usage
verified: 2026-03-23T22:00:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 3: Coordinator + Usage Verification Report

**Phase Goal:** The integration actively polls the Flume sensor and exposes per-zone daily water usage as HA sensor entities that persist correctly across restarts and midnight boundaries
**Verified:** 2026-03-23T22:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

Truths are drawn from the `must_haves` sections of Plans 03-01 and 03-02, then verified directly in the codebase and confirmed by live test execution.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Coordinator polls Flume sensor and returns ZoneData per monitored zone | VERIFIED | `_async_update_data` reads `CONF_FLUME_ENTITY_ID` state, builds `dict[str, ZoneData]`; `test_sensor_entities_created` PASSED |
| 2 | Daily usage accumulates while zone runs and persists in Store across restarts | VERIFIED | `_daily_totals` accumulated each poll interval; `_flush_store` callback on unload calls `async_save`; `test_totals_persist_across_restart` PASSED |
| 3 | Startup with stale stored date resets totals to 0 | VERIFIED | `_async_setup` compares `stored["date"]` to `date.today().isoformat()`; resets to `{}` on mismatch; `test_stale_date_resets_totals` PASSED |
| 4 | Midnight callback resets daily totals and saves to Store | VERIFIED | `async_track_time_change(hour=0, minute=0, second=0)` registered in `_async_setup`; `_midnight_reset` zeroes `_daily_totals`; `test_midnight_reset_zeroes_totals` PASSED |
| 5 | Flume unavailable raises UpdateFailed making all entities unavailable | VERIFIED | Guard in `_async_update_data` raises `UpdateFailed` on `STATE_UNAVAILABLE`/`STATE_UNKNOWN`; `CoordinatorEntity.available` returns `last_update_success`; `test_flume_unavailable_entities_unavailable` PASSED |
| 6 | valve domain zones detected as running via 'open' state not 'on' | VERIFIED | `_zone_is_on` checks `entity_id.split(".")[0] == "valve"` and uses `state.state == "open"` branch; conftest has `valve.os_zone_3` fixture |
| 7 | A daily_usage sensor entity appears for each monitored zone | VERIFIED | `DailyUsageSensor` created per zone in `async_setup_entry`; explicit `entity_id = f"sensor.{DOMAIN}_{zone_slug}_daily_usage"`; `test_sensor_entities_created` PASSED |
| 8 | A flow_rate sensor entity appears for each monitored zone (0 when idle) | VERIFIED | `FlowRateSensor` created per zone; returns `zone.flow_rate` which is `0.0` when `_zone_is_on` is False; `test_flow_rate_zero_when_idle` PASSED |
| 9 | After HA restart mid-day, daily usage resumes from stored total | VERIFIED | `_async_setup` restores `_daily_totals` from Store when date matches today; `test_totals_persist_across_restart` PASSED |
| 10 | If HA was offline at midnight, daily totals reset on next startup | VERIFIED | Stale-date path in `_async_setup` resets `_daily_totals = {}`; confirmed by `test_stale_date_resets_totals` PASSED |
| 11 | When Flume is unavailable, all sensor entities show unavailable | VERIFIED | `UpdateFailed` propagates to `last_update_success=False`; `CoordinatorEntity.available` returns False; HA writes `unavailable` state |
| 12 | Midnight resets daily usage to 0 for all zones | VERIFIED | `_midnight_reset` sets `self._daily_totals = {z: 0.0 for z in self._daily_totals}`; confirmed by passing test |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/irrigation_monitor/coordinator.py` | IrrigationCoordinator + ZoneData dataclass | VERIFIED | 168 lines; both classes present and substantive |
| `custom_components/irrigation_monitor/sensor.py` | DailyUsageSensor + FlowRateSensor + async_setup_entry | VERIFIED | 93 lines (exceeds min_lines: 50); all three exports present |
| `custom_components/irrigation_monitor/__init__.py` | Entry setup wiring coordinator to runtime_data, forwarding sensor platform | VERIFIED | `entry.runtime_data = coordinator`; `PLATFORMS = ["sensor"]`; correct ordering: first_refresh → runtime_data → forward_setups |
| `custom_components/irrigation_monitor/const.py` | STORAGE_KEY and SAVE_DELAY constants | VERIFIED | `STORAGE_KEY = "irrigation_monitor.daily_usage"`; `SAVE_DELAY = 30`; `STORAGE_VERSION = 1` |
| `tests/test_coordinator.py` | 7 RED stubs (now GREEN) covering all USAGE requirements | VERIFIED | 218 lines; 7 test functions confirmed by `grep -c "def test_"` |
| `tests/conftest.py` | mock_config_entry fixture for coordinator tests | VERIFIED | Fixture present at line 71; wires mock_flume_entity + mock_valve_entities into MockConfigEntry |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `__init__.py` | `coordinator.py` | `IrrigationCoordinator(hass, entry)` + `async_config_entry_first_refresh` | WIRED | Line 17: `coordinator = IrrigationCoordinator(hass, entry)`; line 18: `await coordinator.async_config_entry_first_refresh()` |
| `coordinator.py` | `homeassistant.helpers.storage.Store` | `async_delay_save` for daily totals persistence | WIRED | 3 calls to `async_delay_save` (lines 64, 144, 167); none are awaited (correct — `@callback`); plus explicit `async_save` on unload |
| `coordinator.py` | `homeassistant.helpers.event` | `async_track_time_change` for midnight reset | WIRED | Imported at line 11; used at line 67 with `hour=0, minute=0, second=0`; unsubscribe registered on entry unload |
| `sensor.py` | `coordinator.py` | `entry.runtime_data` access for IrrigationCoordinator | WIRED | Line 25: `coordinator: IrrigationCoordinator = entry.runtime_data` |
| `sensor.py` | `CoordinatorEntity[IrrigationCoordinator]` | Class inheritance for auto-update wiring | WIRED | Both `DailyUsageSensor` and `FlowRateSensor` inherit `CoordinatorEntity[IrrigationCoordinator]` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| USAGE-01 | 03-01, 03-02 | Integration exposes a sensor entity per monitored zone showing daily water usage (gallons accumulated since midnight) | SATISFIED | `DailyUsageSensor` + `FlowRateSensor` per zone; `test_sensor_entities_created` PASSED; REQUIREMENTS.md marked `[x]` |
| USAGE-02 | 03-01, 03-02 | Daily usage totals persist across HA restarts and only reset at midnight (not on restart) | SATISFIED | Store `async_save` on unload; `_async_setup` restores on matching date; midnight callback zeroes; `test_totals_persist_across_restart` + `test_midnight_reset_zeroes_totals` PASSED; REQUIREMENTS.md marked `[x]` |
| USAGE-03 | 03-01, 03-02 | If HA was offline at midnight, daily totals reset correctly on next startup based on stored date comparison | SATISFIED | Stale-date check in `_async_setup`; `test_stale_date_resets_totals` PASSED; REQUIREMENTS.md marked `[x]` |

No orphaned requirements found — REQUIREMENTS.md maps only USAGE-01/02/03 to Phase 3, and both plans claim all three.

---

### Anti-Patterns Found

None. Scanned all six phase-modified files for:
- TODO/FIXME/PLACEHOLDER/XXX comments — none found
- Empty return stubs (`return {}`, `return []`, `return null`) — none found
- Custom `available` property override in sensor.py — absent (correct: CoordinatorEntity handles it)
- `await.*async_delay_save` — absent (correct: `async_delay_save` is `@callback`, must not be awaited)

---

### Human Verification Required

The following behaviors are correct in code and tests but cannot be verified programmatically:

#### 1. Entity Visibility in HA UI

**Test:** Install the integration in a live HA instance with a configured entry, then navigate to Settings > Entities.
**Expected:** Two entities per monitored zone appear — `sensor.irrigation_monitor_{zone_slug}_daily_usage` and `sensor.irrigation_monitor_{zone_slug}_flow_rate` — with correct device class icons (water drop, flow rate).
**Why human:** Entity registry display, icons, and UI labels require a running HA instance.

#### 2. Midnight Reset at System Boundary

**Test:** Let the integration run through a real midnight while a zone is active. Check entity states at 00:00:01.
**Expected:** All daily_usage sensors reset to 0.0 and begin accumulating again for the new day.
**Why human:** Real-time behavior crossing midnight cannot be verified by unit tests without system clock manipulation.

#### 3. Store Persistence on HA Stop (Non-Unload Path)

**Test:** Accumulate usage, stop HA via `ha core stop` (not config entry unload), restart, verify daily_usage sensors reflect pre-shutdown values.
**Expected:** Totals resume from persisted Store values.
**Why human:** The `_flush_store` path is tested via entry unload; `EVENT_HOMEASSISTANT_FINAL_WRITE` path requires actual HA lifecycle. Tests confirmed the unload path works; the HA-stop path is architecturally sound but needs live verification.

---

### Gaps Summary

No gaps. All 12 truths verified, all 6 artifacts substantive and wired, all 5 key links confirmed, all 3 requirements satisfied by passing tests.

The phase goal — "The integration actively polls the Flume sensor and exposes per-zone daily water usage as HA sensor entities that persist correctly across restarts and midnight boundaries" — is fully achieved.

Test evidence:
- `7/7 tests in tests/test_coordinator.py PASSED`
- `20/20 tests in full suite PASSED (zero regressions from Phase 2)`

---

_Verified: 2026-03-23T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
