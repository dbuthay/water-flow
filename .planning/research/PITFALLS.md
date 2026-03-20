# Pitfalls: Home Assistant Custom Integration Development

**Domain:** HA custom integration + Lovelace card
**Focus:** State persistence, config/options flow, HACS compliance, automation/monitoring logic

---

## P1 — Blocking the HA Event Loop

**Pitfall:** Running synchronous I/O (file reads, sleep, HTTP calls) in entity methods or coordinator `_async_update_data`.

**Warning signs:** HA logs show "Detected blocking call in the event loop"; integration feels sluggish.

**Prevention:**
- All coordinator and entity methods must be `async`
- Use `await asyncio.sleep()` not `time.sleep()`
- Use `aiohttp` or `hass.async_add_executor_job()` for any blocking calls
- The calibration sequence must use `async_track_point_in_time` or `asyncio.sleep` for delays

**Phase:** Phase 1 (set pattern from the start)

---

## P2 — Calibration Data Lost on HA Restart

**Pitfall:** Storing calibrated flow values in `coordinator.__init__` or `hass.data[DOMAIN]` (in-memory only). Lost on every HA restart.

**Warning signs:** After HA restart, all zones show uncalibrated state; leak detection stops working.

**Prevention:**
- Store calibration in `ConfigEntry.options` (persisted to `.storage/core.config_entries`)
- Use `hass.config_entries.async_update_entry(entry, options={...})` to write
- Daily usage totals → `homeassistant.helpers.storage.Store` (separate file, frequent writes)

**Phase:** Phase 2 (config entry design), Phase 3 (coordinator), Phase 4 (calibration)

---

## P3 — Options Flow Destroys Existing Zone Config

**Pitfall:** Options flow handler overwrites the entire `entry.options` dict when saving, wiping calibration data for zones not shown in the current form step.

**Warning signs:** Running options flow to add a new valve resets calibration on all existing valves.

**Prevention:**
```python
# WRONG:
return self.async_create_entry(data={"zones": new_zones})

# RIGHT — merge, don't replace:
existing = dict(self.config_entry.options)
existing["zones"] = new_zones  # only update what changed
return self.async_create_entry(data=existing)
```

**Phase:** Phase 2 (options flow implementation)

---

## P4 — Race Condition: Coordinator Reads Before Zone State Settles

**Pitfall:** Coordinator polls Flume immediately after a valve switch is called. The valve hasn't physically opened yet (mechanical delay), so flow reads zero, and the system mis-reports or mis-calibrates.

**Warning signs:** Calibration records 0.0 gal/min; leak detection triggers immediately after zone start.

**Prevention:**
- Add a configurable `ZONE_START_DELAY` (default 5s) before reading flow after a zone turns on
- During calibration, use `STABILIZATION_DELAY` (default 30s) before sampling
- In leak detection, skip the first N polls after zone state changes to ON

**Phase:** Phase 3 (coordinator), Phase 4 (calibration), Phase 5 (leak detection)

---

## P5 — Flume Sensor Unavailable / Unknown State

**Pitfall:** Flume integration is cloud-dependent. If Flume's servers are unreachable, the sensor state becomes `unavailable` or `unknown`. String-to-float conversion crashes the coordinator.

**Warning signs:** `ValueError: could not convert string to float: 'unavailable'`; coordinator stops updating.

**Prevention:**
```python
state = hass.states.get("sensor.flume_flow")
if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
    raise UpdateFailed("Flume sensor unavailable")
flow = float(state.state)
```
- Never assume the sensor state is a valid number
- Propagate `UpdateFailed` from coordinator so HA shows the integration as unavailable

**Phase:** Phase 3 (coordinator)

---

## P6 — Entity Uniqueness / Duplicate Entities After Config Change

**Pitfall:** Changing how entity unique IDs are constructed between versions (or after options flow update) creates duplicate entities in HA's entity registry.

**Warning signs:** Entity list shows `sensor.wfm_zone_1_daily_usage_2` duplicates.

**Prevention:**
- Set unique_id at entity creation: `f"{entry.entry_id}_{zone_id}_daily_usage"`
- Never change the unique_id format after release
- When adding zones via options flow, generate new entities only for truly new zone IDs

**Phase:** Phase 3 (entity registration)

---

## P7 — HACS Submission Failures

**Pitfall:** PR to HACS default fails validation checks that aren't obvious from docs.

**Common failures:**
- Missing `version` in `manifest.json`
- `hacs.json` not at repo root
- No semver git tag matching `manifest.json` version
- `custom_components/` not at repo root (nested in subdirectory)
- `codeowners` in `manifest.json` doesn't match GitHub username exactly

**Prevention:**
- Run `hacs-validate` CLI tool before submission
- Use GitHub Actions workflow: `hacs/action@main` to validate on every push
- Test HACS install locally by adding repo as custom repository before submitting to default

**Phase:** Phase 1 (project setup)

---

## P8 — Lovelace Card Not Loading / Caching Issues

**Pitfall:** After updating the card JS file, HA serves the cached version. Users (and you in dev) see old behavior.

**Warning signs:** Changes to `water-flow-card.js` don't take effect; hard refresh required.

**Prevention:**
- Append `?v=VERSION` to the resource URL in Lovelace config
- In HACS, the resource URL is managed automatically — use HACS resource management
- In dev, use `?v=dev_$(date +%s)` to bust cache

**Phase:** Phase 7 (Lovelace card)

---

## P9 — Midnight Reset Missed If HA Was Down

**Pitfall:** If HA is offline at midnight, the `async_track_time_change` callback never fires. Daily totals from yesterday carry into today.

**Warning signs:** Daily usage counter never resets; accumulates indefinitely.

**Prevention:**
- On coordinator startup, check if stored date != today. If different, reset totals before loading.
```python
stored_date = self._store_data.get("date")
if stored_date != date.today().isoformat():
    self._reset_daily_totals()
    self._store_data["date"] = date.today().isoformat()
```

**Phase:** Phase 3 (coordinator + storage)

---

## P10 — Calibration While Zone Is Already Running

**Pitfall:** User presses calibrate while the zone is already ON (e.g., scheduled run in progress). Integration tries to turn zone ON again, or worse, turns it OFF at the end of calibration during an active schedule.

**Warning signs:** Calibration disrupts active irrigation schedule.

**Prevention:**
- Check zone state before starting calibration
- If zone is already ON: abort with notification "Zone is currently running — stop it first"
- Log a warning and surface it as a persistent notification

**Phase:** Phase 4 (calibration)
