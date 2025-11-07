# Food Tax Automation Feature

## Overview
Automated food tax collection system that applies taxes to teams at regular intervals based on game difficulty and duration. The system is pause-aware, provides advance warnings, and handles special building effects.

## Key Features

### 1. Difficulty-Based Tax Intervals
Tax collection intervals scale based on both difficulty level and game duration:

#### Default 90-Minute Game
- **Easy**: 20 minutes
- **Medium**: 15 minutes
- **Hard**: 10 minutes

#### 60-Minute Game (Scaled)
- **Easy**: 15 minutes
- **Medium**: 11 minutes
- **Hard**: 7 minutes

#### Other Durations (120, 150, 180, 210, 240 minutes)
All durations have proportionally scaled intervals defined in `TAX_INTERVALS` constant in `food_tax_manager.py`.

### 2. School Building Effect
When a team has built a School:
- Food tax increases by **50%**
- Developed nations: 15 → 22 food
- Developing nations: 5 → 7 food

This balances the School's benefit of allowing individual production without full team.

### 3. Restaurant Bonus
When food tax is successfully paid (not during famine):
- Each restaurant generates **5 currency per food unit** taxed
- Example: 15 food tax with 2 restaurants = 150 currency bonus
- Already implemented in `GameLogic.apply_food_tax()`

### 4. Famine Penalty
When a team cannot pay the food tax:
- Must pay **2x bank price in currency** for shortfall
- Example: Short 10 food, bank price 2 currency/food = 40 currency penalty
- Food reduced to 0, all available food consumed
- If cannot afford currency penalty, tax application fails

### 5. Pause-Aware Timing
- Tax timers pause when game is paused
- On resume, all pending tax due times are adjusted by pause duration
- Similar to challenge system implementation
- Frontend calls `/api/v2/food-tax/{game_code}/adjust-for-pause` on resume

### 6. Warning System
- Teams receive a warning **3 minutes before** tax is due
- Warning sent via WebSocket event `food_tax_warning`
- Visual notification shown to affected team
- Warning flag prevents duplicate notifications

### 7. Automatic Collection
- Background scheduler checks all active games every **30 seconds**
- No banker intervention required
- Food automatically deducted from team resources
- Food added to bank inventory
- WebSocket events notify all players

## Architecture

### Backend Components

#### 1. `food_tax_manager.py`
Core business logic for food tax operations:
- **FoodTaxManager** class
  - `get_tax_interval_minutes()` - Calculate interval based on difficulty/duration
  - `calculate_food_tax_amount()` - Calculate tax with School effect
  - `initialize_food_tax_tracking()` - Set up tracking when game starts
  - `adjust_for_pause()` - Adjust timings after pause
  - `check_and_process_taxes()` - Main periodic check function
  - `get_tax_status()` - Get current status for all teams
  - `force_apply_tax()` - Manual trigger (banker action)

#### 2. `food_tax_api.py`
REST API endpoints:
- `GET /api/v2/food-tax/{game_code}/status` - Get tax status
- `POST /api/v2/food-tax/{game_code}/adjust-for-pause` - Adjust for pause
- `POST /api/v2/food-tax/{game_code}/force-apply` - Manual trigger
- `POST /api/v2/food-tax/{game_code}/initialize` - Initialize tracking

#### 3. `food_tax_scheduler.py`
Background task system:
- `food_tax_scheduler()` - Main async task loop (runs every 30 seconds)
- `check_all_games_for_taxes()` - Process all active games
- `on_game_started()` - Initialize tracking when game starts
- `on_game_paused()` - Log pause event
- `on_game_resumed()` - Adjust timings after resume
- `on_game_ended()` - Clean up when game ends

#### 4. Integration in `main.py`
- Food tax API router included
- Scheduler started on app startup
- Scheduler stopped on app shutdown
- Event handlers called on game state changes

### Frontend Components

#### 1. `food-tax-manager.js`
Frontend manager class:
- **FoodTaxManager** class
  - `initialize()` - Load initial tax status
  - `loadTaxStatus()` - Fetch status from API
  - `adjustForPause()` - Call API to adjust timings
  - `startTimer()` / `stopTimer()` - Manage countdown display updates
  - `updateUI()` - Update dashboard displays
  - `updatePlayerUI()` - Player-specific display
  - `updateHostBankerUI()` - Host/banker overview
  - Event handlers for WebSocket events
  - Notification system

#### 2. Integration in `dashboard.js`
- FoodTaxManager instantiated alongside ChallengeManager
- WebSocket event handlers added for:
  - `food_tax_warning`
  - `food_tax_applied`
  - `food_tax_famine`
- Adjust-for-pause called on game resume
- Resource displays updated when tax events occur

#### 3. UI Components in `dashboard-styles.css`
- `.food-tax-status` - Player view display
- `.food-tax-overview` - Host/banker overview grid
- Color-coded status indicators:
  - **Green** (safe): More than 3 minutes remaining
  - **Yellow** (warning): 1-3 minutes remaining
  - **Red** (critical): Less than 1 minute remaining
- Pulse animations for warnings and critical states

## Database Schema

### GameSession.game_state Structure

```json
{
  "teams": {
    "1": {
      "resources": {...},
      "buildings": {...},
      "nation_type": "nation_1",
      "is_developed": true
    }
  },
  "food_tax": {
    "1": {
      "last_tax_time": "2024-01-15T10:30:00",
      "next_tax_due": "2024-01-15T10:50:00",
      "warning_sent": false,
      "tax_interval_minutes": 20,
      "total_taxes_paid": 5,
      "total_famines": 1
    }
  },
  "bank_inventory": {
    "food": 150,
    "raw_materials": 150,
    ...
  }
}
```

## WebSocket Events

### 1. `food_tax_warning`
Sent 3 minutes before tax is due.

```json
{
  "type": "event",
  "event_type": "food_tax_warning",
  "data": {
    "team_number": "1",
    "minutes_remaining": 2.5,
    "next_tax_due": "2024-01-15T10:50:00"
  }
}
```

### 2. `food_tax_applied`
Sent when tax is successfully paid.

```json
{
  "type": "event",
  "event_type": "food_tax_applied",
  "data": {
    "team_number": "1",
    "tax_amount": 15,
    "success": true,
    "message": "Food tax paid. Restaurants generated 150 currency!",
    "new_resources": {
      "food": 35,
      "currency": 250,
      ...
    },
    "next_tax_due": "2024-01-15T11:10:00",
    "is_famine": false
  }
}
```

### 3. `food_tax_famine`
Sent when team cannot pay food tax.

```json
{
  "type": "event",
  "event_type": "food_tax_famine",
  "data": {
    "team_number": "1",
    "tax_amount": 15,
    "success": true,
    "message": "FAMINE: Paid 40 currency for 10 food shortage",
    "new_resources": {
      "food": 0,
      "currency": 160,
      ...
    },
    "next_tax_due": "2024-01-15T11:10:00",
    "is_famine": true
  }
}
```

## API Reference

### Get Tax Status
```http
GET /api/v2/food-tax/{game_code}/status
```

**Response:**
```json
{
  "success": true,
  "game_code": "ABC123",
  "game_status": "in_progress",
  "teams": {
    "1": {
      "next_tax_due": "2024-01-15T10:50:00",
      "minutes_until_due": 18.5,
      "tax_amount": 22,
      "tax_interval_minutes": 20,
      "warning_sent": false,
      "total_taxes_paid": 3,
      "total_famines": 0,
      "last_tax_time": "2024-01-15T10:30:00"
    }
  }
}
```

### Adjust for Pause
```http
POST /api/v2/food-tax/{game_code}/adjust-for-pause?pause_duration_ms=120000
```

**Response:**
```json
{
  "success": true,
  "adjusted_teams": ["1", "2", "3"],
  "pause_duration_seconds": 120
}
```

### Force Apply Tax
```http
POST /api/v2/food-tax/{game_code}/force-apply?team_number=1
```

**Response:**
```json
{
  "success": true,
  "event": {
    "type": "event",
    "event_type": "food_tax_applied",
    "data": {...}
  }
}
```

## Testing

### Backend Tests (`tests/test_food_tax.py`)

Comprehensive test suite with 40+ tests covering:

#### Tax Interval Calculations
- All difficulty × duration combinations
- Invalid input handling
- Default fallbacks

#### Tax Amount Calculations  
- Developed vs. developing nations
- School building effect (50% increase)
- Multiple schools (no additional effect)

#### Restaurant Bonuses
- Currency generation on successful payment
- No bonus during famine
- Scaling with multiple restaurants

#### Famine Handling
- Currency penalty calculation
- Insufficient currency scenarios
- Resource state updates

#### Pause-Aware Timing
- Time adjustment after pause
- Warning flag reset
- Multiple pause cycles

#### Warning System
- Warning sent at 3-minute threshold
- No duplicate warnings
- Warning flag management

#### Automated Application
- Tax deduction from team
- Food transfer to bank
- Statistics tracking
- Next tax scheduling

#### Tax Status API
- Status retrieval for all teams
- Time calculations
- Statistics reporting

### Running Tests

```bash
cd backend
pytest tests/test_food_tax.py -v
```

Or run specific test classes:
```bash
pytest tests/test_food_tax.py::TestTaxIntervalCalculations -v
pytest tests/test_food_tax.py::TestSchoolEffect -v
```

## User Experience

### Player View
1. **Tax Status Card** appears on player dashboard when game starts
2. **Countdown Timer** shows time until next tax (updates every second)
3. **Warning Notification** appears 3 minutes before tax is due
4. **Tax Applied** notification shows when tax is paid
   - Success: Green notification with restaurant bonus if applicable
   - Famine: Red notification with penalty details
5. **Resource Display** automatically updates after tax event
6. **Statistics** show total taxes paid and famines occurred

### Host/Banker View
1. **Tax Overview Grid** shows all teams' status
2. **Color-Coded Cards** indicate urgency:
   - Green: Safe (>3 minutes)
   - Yellow: Warning (1-3 minutes)
   - Red: Critical (<1 minute)
3. **Statistics** for each team (taxes paid, famines)
4. **Event Log** records all tax events
5. **Manual Trigger** option available via API (optional)

## Configuration

### Tax Intervals
Defined in `food_tax_manager.py`:
```python
TAX_INTERVALS = {
    "easy": {60: 15, 90: 20, 120: 25, ...},
    "medium": {60: 11, 90: 15, 120: 18, ...},
    "hard": {60: 7, 90: 10, 120: 12, ...}
}
```

### Warning Timing
```python
WARNING_BEFORE_TAX_MINUTES = 3  # Warn 3 minutes before
```

### Scheduler Frequency
In `food_tax_scheduler.py`:
```python
await asyncio.sleep(30)  # Check every 30 seconds
```

## Troubleshooting

### Tax Not Being Applied
1. Check game status is `IN_PROGRESS`
2. Verify scheduler is running: logs should show periodic checks
3. Check `game_state['food_tax']` is initialized
4. Verify `next_tax_due` time is in the past

### Timers Not Updating After Pause
1. Ensure `adjustForPause()` is called on resume
2. Check frontend pause duration calculation
3. Verify API endpoint `/adjust-for-pause` is accessible
4. Check browser console for errors

### Warning Not Showing
1. Verify `warning_sent` flag is `false` in game state
2. Check WebSocket connection is active
3. Ensure FoodTaxManager is initialized on frontend
4. Check notification permissions in browser

### Bank Not Receiving Food
1. Verify `bank_inventory` exists in `game_state`
2. Check tax was successfully paid (not famine)
3. Review backend logs for errors in `_apply_tax_to_team()`

## Future Enhancements

Potential additions for future versions:

1. **Variable Tax Rates**
   - Allow banker to adjust tax rates dynamically
   - Seasonal variations (higher in winter months)

2. **Tax Relief Events**
   - Special events that waive tax for a period
   - Reduced tax rates for struggling teams

3. **Advanced Statistics**
   - Tax history graphs
   - Comparative team analysis
   - Tax efficiency metrics

4. **Notifications**
   - Browser push notifications for warnings
   - Email notifications for host
   - SMS alerts (optional)

5. **Tax Policy Options**
   - Progressive taxation (higher for wealthier teams)
   - Flat tax vs. graduated rates
   - Tax holidays

## Files Modified/Created

### Backend
- ✅ `backend/food_tax_manager.py` (new)
- ✅ `backend/food_tax_api.py` (new)
- ✅ `backend/food_tax_scheduler.py` (new)
- ✅ `backend/main.py` (modified - added imports and integrations)
- ✅ `backend/tests/test_food_tax.py` (new)

### Frontend
- ✅ `frontend/food-tax-manager.js` (new)
- ✅ `frontend/dashboard.js` (modified - added event handlers and integration)
- ✅ `frontend/dashboard.html` (modified - added script import)
- ✅ `frontend/dashboard-styles.css` (modified - added food tax styles)

### Documentation
- ✅ `FEATURE-FOOD-TAX-AUTOMATION.md` (this file)

## Status

✅ **Complete and Ready for Testing**

All core features implemented:
- Difficulty-based tax intervals
- School building effect
- Restaurant bonuses
- Famine penalties
- Pause-aware timing
- Warning system
- Automatic collection
- WebSocket integration
- UI displays and notifications
- Comprehensive test suite

## Credits

Implementation follows the established patterns from:
- Challenge system (pause-aware timing, WebSocket events)
- Trading system (manager class pattern)
- Pricing system (game state management)
