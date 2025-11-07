# Food Tax System - Quick Start Guide

## Testing the Feature

### 1. Start the Servers

```bash
cd /home/runner/work/TheTradingGame/TheTradingGame
./restart-servers.sh
```

This starts:
- Backend on port 8000
- Frontend on port 3000

### 2. Create a Game

1. Navigate to `http://localhost:3000`
2. Click "Create Game" or "Join Game"
3. Set up game settings:
   - Choose difficulty (Easy/Medium/Hard)
   - Set game duration (60/90/120/etc. minutes)
   - Assign teams to players

### 3. Observe Food Tax in Action

Once the game starts, you'll see:

#### For Players:
- **Food Tax Status Card** at top of production section
  - Shows tax amount
  - Countdown timer
  - Statistics (taxes paid, famines)

#### For Host/Banker:
- **Food Tax Overview** in banker dashboard
  - Grid showing all teams
  - Color-coded status indicators
  - Real-time countdowns

### 4. Test Scenarios

#### Scenario 1: Normal Tax Payment
1. Start game with sufficient food
2. Wait for tax to be due (or reduce interval for testing)
3. Observe:
   - Warning notification at 3 minutes
   - Automatic deduction when due
   - Food transferred to bank
   - Restaurant bonus if applicable

#### Scenario 2: Famine (Insufficient Food)
1. Use resources until food is low
2. Wait for tax due
3. Observe:
   - Currency penalty applied
   - Famine notification shown
   - Statistics updated

#### Scenario 3: School Building Effect
1. Build a school
2. Wait for next tax cycle
3. Observe:
   - Tax amount increased by 50%
   - Display shows higher amount

#### Scenario 4: Pause/Resume
1. Pause the game (host action)
2. Wait a few minutes
3. Resume the game
4. Observe:
   - Tax timers adjusted correctly
   - No tax applied during pause
   - Countdowns continue from adjusted time

## Quick Tax Interval Reference

### 60-Minute Game
- Easy: Every 15 minutes
- Medium: Every 11 minutes
- Hard: Every 7 minutes

### 90-Minute Game (Default)
- Easy: Every 20 minutes
- Medium: Every 15 minutes
- Hard: Every 10 minutes

### 120-Minute Game
- Easy: Every 25 minutes
- Medium: Every 18 minutes
- Hard: Every 12 minutes

## Tax Amounts

### Base Amounts
- **Developed Nations**: 15 food
- **Developing Nations**: 5 food

### With School Building
- **Developed Nations**: 22 food (15 × 1.5)
- **Developing Nations**: 7 food (5 × 1.5)

## Testing with Shorter Intervals (Development)

To test more quickly, you can temporarily modify tax intervals:

1. Edit `backend/food_tax_manager.py`
2. Find the `TAX_INTERVALS` constant
3. Change values to shorter times (e.g., 1 minute for testing)
4. Restart backend server

Example for rapid testing:
```python
TAX_INTERVALS = {
    "easy": {60: 2, 90: 2, 120: 2, ...},
    "medium": {60: 1, 90: 1, 120: 1, ...},
    "hard": {60: 1, 90: 1, 120: 1, ...}
}
```

**Remember to revert these changes after testing!**

## API Testing

### Get Tax Status
```bash
curl http://localhost:8000/api/v2/food-tax/ABC123/status
```

### Force Apply Tax (Manual Trigger)
```bash
curl -X POST "http://localhost:8000/api/v2/food-tax/ABC123/force-apply?team_number=1"
```

### Adjust for Pause
```bash
curl -X POST "http://localhost:8000/api/v2/food-tax/ABC123/adjust-for-pause?pause_duration_ms=120000"
```

## Checking Backend Logs

```bash
# Real-time log monitoring
tail -f /tmp/trading-game-backend.log

# Search for food tax events
grep "Food tax" /tmp/trading-game-backend.log

# Check scheduler activity
grep "food_tax_scheduler" /tmp/trading-game-backend.log
```

## Browser Console Monitoring

Open browser DevTools (F12) and look for:

```javascript
// Food tax manager initialization
[FoodTaxManager] Initializing...
[FoodTaxManager] Tax status loaded: {...}

// Warning events
[FoodTaxManager] Warning received: {...}

// Tax application
[FoodTaxManager] Tax applied: {...}

// Famine events
[FoodTaxManager] Famine occurred: {...}
```

## Common Test Cases

### Test Case 1: First Tax Payment
**Setup:**
- New game
- Default settings (90 min, medium difficulty)

**Expected:**
- First tax due: 15 minutes after game start
- Warning at: 12 minutes after game start
- Payment: 15 food deducted at 15 minutes

### Test Case 2: Restaurant Bonus
**Setup:**
- Team has 2 restaurants
- Sufficient food (30+)

**Expected:**
- Tax paid: 15 food deducted
- Bonus received: 150 currency (15 × 5 × 2)
- Notification shows bonus amount

### Test Case 3: School Tax Increase
**Setup:**
- Team builds school
- Developed nation

**Expected:**
- Tax amount: 22 food (was 15)
- Display updated to show new amount

### Test Case 4: Famine Scenario
**Setup:**
- Team has 5 food
- Tax due: 15 food
- Team has 100+ currency

**Expected:**
- Shortage: 10 food
- Penalty: 40 currency (10 × 2 × 2)
- Food: 0
- Currency: reduced by 40
- Famine notification shown

### Test Case 5: Pause/Resume
**Setup:**
- Game in progress
- Tax due in 10 minutes

**Actions:**
1. Pause game
2. Wait 5 minutes (real time)
3. Resume game

**Expected:**
- Tax still due in 10 minutes (not 5)
- Countdown adjusted for pause
- No tax applied during pause

## Troubleshooting Tips

### Food Tax Not Appearing
1. Check game has started (status = IN_PROGRESS)
2. Verify teams are assigned
3. Check browser console for errors
4. Refresh dashboard

### Timer Not Counting Down
1. Check FoodTaxManager is initialized
2. Verify WebSocket connection
3. Look for JavaScript errors in console
4. Check backend scheduler is running

### Tax Not Applied Automatically
1. Check backend logs for scheduler activity
2. Verify game status is IN_PROGRESS
3. Check `next_tax_due` time in database
4. Ensure food_tax tracking is initialized

### Warning Not Received
1. Check WebSocket connection
2. Verify warning time threshold (3 minutes)
3. Check `warning_sent` flag in game state
4. Look for WebSocket events in Network tab

## Performance Notes

- Scheduler runs every 30 seconds (low impact)
- Frontend timer updates every second (minimal CPU)
- WebSocket events are efficient (only when needed)
- Database writes only on tax application (not on checks)

## Production Considerations

Before deploying to production:

1. ✅ Verify all tests pass
2. ✅ Test with multiple concurrent games
3. ✅ Monitor scheduler performance
4. ✅ Set up backend logging
5. ✅ Configure WebSocket error handling
6. ✅ Test with different network conditions
7. ✅ Verify pause/resume behavior
8. ✅ Test browser notification permissions

## Support

If you encounter issues:

1. Check `FEATURE-FOOD-TAX-AUTOMATION.md` for detailed documentation
2. Review test cases in `backend/tests/test_food_tax.py`
3. Check backend logs: `/tmp/trading-game-backend.log`
4. Review browser console for JavaScript errors
5. Verify API endpoints are accessible
6. Check WebSocket connection status

## Next Steps

After successful testing:

1. Test with real players in a full game session
2. Gather feedback on timing and balance
3. Monitor for any edge cases
4. Consider adjusting tax intervals if needed
5. Document any additional issues found
6. Plan for future enhancements (see FEATURE-FOOD-TAX-AUTOMATION.md)
