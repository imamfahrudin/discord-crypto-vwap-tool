# Bot Scheduler Timer Reset Fix

## Problem Identified ❌

When a session change occurred, the bot would:
1. ✅ Update all messages immediately via `perform_single_update()`
2. ❌ **NOT reset the timer loops** - they continued with original schedule
3. ❌ This caused double updates close together instead of proper interval spacing

### Example Issue:
- Scanner with 60s interval last updated at 10:00:00 (next scheduled: 10:01:00)
- Session changes at 10:00:30
- Immediate update happens at 10:00:30 ✅
- Loop still wakes up at 10:01:00 and updates again ❌ (only 30s later!)
- **Expected**: Next update at 10:01:30 (60s after session change)

## Solution Implemented ✅

### 1. Added Timer Reset Event
Added `asyncio.Event` to each channel/interval state:
```python
'reset_timer_event': asyncio.Event()  # Signal to reset timer
```

### 2. Modified Update Loop
Changed from simple `asyncio.sleep()` to event-based waiting:
```python
# Old: Just sleep for interval
await asyncio.sleep(interval)

# New: Wait for either timeout OR reset signal
reset_event = self.channel_states[channel_id][interval]['reset_timer_event']
try:
    await asyncio.wait_for(reset_event.wait(), timeout=interval)
    # Event triggered = session change, reset timer
    reset_event.clear()
except asyncio.TimeoutError:
    # Normal timeout = interval elapsed
    pass
```

### 3. Simplified Session Change Handler
Instead of creating separate update tasks, just signal the existing loops:
```python
# Old: Create separate update tasks that don't affect timers
task = asyncio.create_task(self.perform_single_update(channel_id, interval))

# New: Signal reset event to interrupt sleep and reset timer
reset_event = self.channel_states[channel_id][interval]['reset_timer_event']
reset_event.set()
```

### 4. Removed Redundant Code
Deleted `perform_single_update()` function - no longer needed since the main loop handles everything.

## How It Works Now ✅

### Normal Update Cycle:
1. Loop performs update
2. Waits `interval` seconds using `wait_for(reset_event, timeout=interval)`
3. Timeout occurs → loop continues to next update
4. Timer spacing: Exactly `interval` seconds between updates

### Session Change Update:
1. Session monitor detects change
2. Sets `reset_timer_event` for all active scanners
3. Loops wake up immediately (interrupt sleep)
4. Loops clear the event and continue to next update
5. **Timer resets**: Next update happens `interval` seconds from NOW

### Bot Restart Update:
1. `restore_channel_states()` loads saved states
2. Creates tasks with `first_update = True` flag
3. Immediate update occurs
4. Normal timer cycle begins

## Testing Checklist ✅

- [ ] Bot starts and performs immediate updates
- [ ] Regular interval updates work correctly (spacing matches config)
- [ ] Session changes trigger immediate updates
- [ ] Timers reset after session change (next update is `interval` seconds later)
- [ ] Multiple intervals per channel work independently
- [ ] Multiple channels work simultaneously
- [ ] Bot restart restores all scanners correctly

## Files Modified

- `notifier/discord_bot.py`:
  - Added `reset_timer_event` to state initialization (2 places)
  - Modified `update_loop_for_channel()` to use event-based waiting
  - Simplified `trigger_all_updates()` to signal events instead of creating tasks
  - Removed `perform_single_update()` function (no longer needed)
