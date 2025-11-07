# Event System Implementation Summary

Implementation details for the game events system backend.

## Overview

The event system adds dynamic challenges and opportunities through 8 event types (natural disasters, economic events, and positive events) with difficulty scaling, severity levels, and mitigation mechanics.

## Architecture

### Components

```
backend/
├── models.py                    # Event enums and GameEventInstance model
├── event_manager.py             # Business logic for event handling
├── event_api.py                 # REST API endpoints
├── event_config.json            # Event configuration and specifications
├── food_tax_manager.py          # Integration with food tax cycles
└── tests/test_event_system.py  # Comprehensive test suite (19 tests)

docs/
├── EVENT_SYSTEM.md              # User-facing documentation
└── EVENT_SYSTEM_IMPLEMENTATION.md  # This file
```

### Data Models

**Event Enums** (`models.py`):
```python
class EventCategory(str, enum.Enum):
    NATURAL_DISASTER = "natural_disaster"
    ECONOMIC_EVENT = "economic_event"
    POSITIVE_EVENT = "positive_event"

class EventType(str, enum.Enum):
    EARTHQUAKE = "earthquake"
    FIRE = "fire"
    DROUGHT = "drought"
    PLAGUE = "plague"
    BLIZZARD = "blizzard"
    TORNADO = "tornado"
    ECONOMIC_RECESSION = "economic_recession"
    AUTOMATION_BREAKTHROUGH = "automation_breakthrough"

class EventStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CURED = "cured"
```

**Database Model** (`GameEventInstance`):
```python
class GameEventInstance(Base):
    __tablename__ = "game_event_instances"
    
    id = Column(Integer, primary_key=True)
    game_session_id = Column(Integer, ForeignKey("game_sessions.id"))
    event_type = Column(Enum(EventType))
    event_category = Column(Enum(EventCategory))
    severity = Column(Integer)  # 1-5
    status = Column(Enum(EventStatus))
    event_data = Column(JSON)  # Event-specific data
    duration_cycles = Column(Integer, nullable=True)
    cycles_remaining = Column(Integer, nullable=True)
    triggered_at = Column(DateTime)
    expires_at = Column(DateTime, nullable=True)
```

**Game State Storage**:
Events also stored in `game.game_state['active_events']` for quick access:
```json
{
  "active_events": {
    "drought": {
      "production_modifier": 0.5,
      "severity": 3,
      "cycles_remaining": 2,
      "difficulty_modifier": 1.0
    },
    "plague": {
      "infected_teams": ["1", "3"],
      "base_penalty": 0.3,
      "cure_cost": 5,
      "severity": 3
    }
  }
}
```

---

## Event Manager Service

Core business logic in `event_manager.py` (28.7KB).

### Key Methods

#### Difficulty & Scaling
```python
def get_difficulty_modifier(self, game: GameSession) -> float:
    """Returns 0.75 (easy), 1.0 (normal), or 1.5 (hard)"""

def calculate_final_effect(self, base_effect, severity, difficulty_mod, mitigation=1.0):
    """Formula: Base × Severity × Difficulty × Mitigation"""

def get_mitigation_multiplier(self, team, building_type) -> float:
    """Returns 0.0-1.0 based on mitigation buildings (20% per building, max 5)"""
```

#### Event Triggers
Each event type has a trigger method:
```python
def trigger_earthquake(self, game, severity=3) -> GameEventInstance
def trigger_fire(self, game, severity=3) -> GameEventInstance
def trigger_drought(self, game, severity=3) -> GameEventInstance
def trigger_plague(self, game, severity=3) -> GameEventInstance
def trigger_blizzard(self, game, severity=3) -> GameEventInstance
def trigger_tornado(self, game, severity=3) -> GameEventInstance
def trigger_economic_recession(self, game, severity=3) -> GameEventInstance
def trigger_automation_breakthrough(self, game, severity=3, target_team=None) -> GameEventInstance
```

#### Lifecycle Management
```python
def process_food_tax_cycle(self, game: GameSession):
    """Called automatically by food tax scheduler.
    Decrements cycles_remaining, expires events at zero."""

def get_active_events(self, game: GameSession) -> List[Dict]:
    """Returns list of all active events for a game"""

def cure_plague(self, game, team_number: str) -> bool:
    """Cures plague for specific team"""

def complete_automation_breakthrough(self, game, team_number: str) -> bool:
    """Activates automation bonus after payment"""
```

---

## Event Implementation Details

### Earthquake
**File**: `event_manager.py:108-134`

**Logic**:
1. Calculate buildings to destroy per team: `severity × difficulty_mod`
2. Apply infrastructure mitigation: `× (1 - infrastructure_count × 0.2)`
3. Cap at 5 buildings per team
4. Call `_destroy_random_buildings()` helper
5. Store affected teams in event data
6. Create EXPIRED event instance (instant event)

**Helper**: `_destroy_random_buildings(team, count)` - Randomly selects and destroys buildings

### Fire
**File**: `event_manager.py:136-191`

**Logic**:
1. Calculate destruction rate: `20% × severity × difficulty_mod`
2. Apply hospital mitigation: `× (1 - hospital_count × 0.2)`
3. For each team with electrical factories:
   - Destroy `factories × destruction_rate` (rounded down)
4. Store affected teams and counts
5. Create EXPIRED event instance

### Drought
**File**: `event_manager.py:193-241`

**Logic**:
1. Calculate production modifier: `0.5 + (3 - severity) × 0.1`
   - Severity 1: 60% production
   - Severity 3: 50% production
   - Severity 5: 30% production
2. Store in `game_state['active_events']['drought']`
3. Create ACTIVE event instance with 2 cycles duration
4. Infrastructure reduces impact during production calculations (not here)

### Plague
**File**: `event_manager.py:243-309`

**Logic**:
1. Calculate production penalty: `30% × severity × difficulty_mod`
2. Calculate cure cost: `5 × difficulty_mod`
3. Randomly infect 1-2 teams (severity-dependent)
4. Store infected teams list, cure cost
5. Create ACTIVE event with duration=None (until cured)
6. Spread during trades (handled in trading logic)

**Cure**: `cure_plague()` removes team from infected list, expires event if all cured

### Blizzard
**File**: `event_manager.py:311-373`

**Logic**:
1. Calculate food tax multiplier: `2.0 × severity × difficulty_mod`
2. Calculate production penalty by difficulty (10%/20%/30%)
3. Store in `game_state['active_events']['blizzard']`
4. Create ACTIVE event with 2 cycles duration
5. Food tax manager applies multiplier during tax
6. Restaurants generate currency rebate (20% of tax)

### Tornado
**File**: `event_manager.py:375-427`

**Logic**:
1. Calculate loss rate: `15% × severity × difficulty_mod`
2. Apply infrastructure mitigation: `× (1 - infrastructure_count × 0.2)`
3. For each resource type in each team:
   - Remove `resource_amount × loss_rate` (rounded down)
4. Store losses per team
5. Create EXPIRED event instance

### Economic Recession
**File**: `event_manager.py:429-483`

**Logic**:
1. Calculate bank price increase: `50% × severity × difficulty_mod`
2. Calculate building cost increase: `25% × severity × difficulty_mod`
3. Calculate duration: `max(0, 2 + (severity - 3))` cycles
4. Store multipliers and restaurant bonus formula
5. Create ACTIVE event instance
6. Infrastructure reduces price increases (applied during trades/builds)

### Automation Breakthrough
**File**: `event_manager.py:485-547`

**Logic**:
1. Calculate production bonus: `50% × severity × difficulty_mod`
2. Calculate electrical goods cost: `30 × difficulty_mod`
3. Select target team (most factories or specified)
4. Store as pending payment with 1 cycle deadline
5. Create ACTIVE event with 2 cycles duration
6. Complete when team pays electrical goods to bank

---

## API Endpoints

**File**: `event_api.py` (10.4KB)

### POST /api/v2/events/games/{game_code}/trigger
Trigger any event type.

**Request**:
```json
{
  "event_type": "earthquake|fire|drought|plague|blizzard|tornado|economic_recession|automation_breakthrough",
  "severity": 1-5,
  "target_team": "1"  // Optional, for team-specific events
}
```

**Response**:
```json
{
  "success": true,
  "message": "🏚️ Earthquake! Buildings destroyed...",
  "event_id": 123,
  "event_data": {...}
}
```

**Authorization**: Banker/Host only (implement role check)

### GET /api/v2/events/games/{game_code}/active
Get list of all active events.

**Response**:
```json
{
  "events": [
    {
      "id": 123,
      "type": "drought",
      "category": "natural_disaster",
      "severity": 3,
      "triggered_at": "2024-11-07T12:00:00Z",
      "cycles_remaining": 1,
      "event_data": {...}
    }
  ]
}
```

### POST /api/v2/events/games/{game_code}/cure-plague
Cure plague for a team (after they pay medicine).

**Request**:
```json
{
  "team_number": "1"
}
```

### POST /api/v2/events/games/{game_code}/complete-automation
Activate automation breakthrough (after team pays electrical goods).

**Request**:
```json
{
  "team_number": "2"
}
```

---

## Integration with Food Tax Scheduler

**File**: `food_tax_manager.py:259-276`

Added to `check_and_process_taxes()` method:

```python
# After applying taxes to teams
if tax_applied:
    try:
        from event_manager import EventManager
        event_mgr = EventManager(self.db)
        event_mgr.process_food_tax_cycle(game)
    except Exception as e:
        logger.error(f"Error processing event cycle: {str(e)}")
```

**Behavior**:
- Triggered once per food tax cycle (when any team is taxed)
- Calls `EventManager.process_food_tax_cycle(game)`
- Decrements `cycles_remaining` for all active events
- Expires events when `cycles_remaining <= 0`
- Updates database event status to EXPIRED
- Removes from `game_state['active_events']`
- Error handling prevents food tax from failing if event processing fails

---

## WebSocket Events

**Broadcast Format**:
```javascript
{
  "type": "event",
  "event_type": "game_event_triggered",
  "data": {
    "event_id": 123,
    "event_type": "earthquake",
    "category": "natural_disaster",
    "severity": 3,
    "message": "🏚️ Earthquake! Buildings destroyed...",
    "event_data": {
      "affected_teams": [...],
      "total_buildings_destroyed": 8
    }
  }
}
```

**Event Types**:
- `game_event_triggered` - New event started
- `plague_cured` - Team cured of plague
- `automation_activated` - Automation breakthrough payment completed

**Broadcasting** (in `event_api.py`):
```python
await ws_manager.broadcast_to_game(game_code, {
    "type": "event",
    "event_type": "game_event_triggered",
    "data": {...}
})
```

---

## Testing

**File**: `tests/test_event_system.py` (18.9KB, 19 tests)

### Test Structure

**Test Classes**:
- `TestEventManager` - Core manager methods
- `TestEarthquakeEvent` - Earthquake triggers and mitigation
- `TestFireEvent` - Fire triggers and hospital mitigation
- `TestDroughtEvent` - Drought duration and production
- `TestPlagueEvent` - Plague infection and cure
- `TestBlizzardEvent` - Blizzard food tax and production
- `TestTornadoEvent` - Tornado resource destruction
- `TestEconomicRecession` - Recession price increases
- `TestAutomationBreakthrough` - Automation payment flow
- `TestEventAPI` - API endpoint testing

### Test Fixtures

```python
@pytest.fixture
def started_game(client, sample_game, db):
    """Creates game with 4 teams and starts it"""
    # Assigns 4 players to different teams
    # Starts game (initializes team resources/buildings)
    # Returns game data
```

### Key Tests

**Difficulty Modifiers**:
```python
def test_difficulty_modifiers(db, started_game):
    # Tests 0.75 (easy), 1.0 (normal), 1.5 (hard)
```

**Mitigation**:
```python
def test_mitigation_multipliers(db):
    # Tests 0%, 20%, 60%, 100% reduction
```

**Event Lifecycle**:
```python
def test_drought_duration_tracking(db, started_game):
    # Triggers drought (2 cycles)
    # Processes 1 tax cycle
    # Verifies cycles_remaining = 1
    # Processes 2nd cycle
    # Verifies drought removed
```

**API Integration**:
```python
def test_trigger_earthquake_endpoint(client, started_game):
    # POST to /api/v2/events/games/{code}/trigger
    # Verifies response and event creation
```

### Running Tests

```bash
# All event tests
pytest tests/test_event_system.py -v

# Specific test class
pytest tests/test_event_system.py::TestEarthquakeEvent -v

# Single test
pytest tests/test_event_system.py::TestEventManager::test_difficulty_modifiers -v

# With coverage
pytest tests/test_event_system.py --cov=event_manager --cov-report=html
```

---

## Configuration

**File**: `event_config.json` (8.1KB)

Complete event specifications in JSON format for easy balancing.

**Structure**:
```json
{
  "events": {
    "earthquake": {
      "name": "Earthquake",
      "icon": "🏚️",
      "category": "natural_disaster",
      "base_effect": 1.0,
      "max_effect": 5,
      "duration_cycles": 0,
      "targets": "buildings",
      "mitigation": {...},
      "difficulty_scaling": true,
      "formula": "..."
    }
  },
  "difficulty_modifiers": {...},
  "severity_guidelines": {...},
  "event_scheduling_recommendations": {...},
  "mitigation_buildings": {...}
}
```

---

## Future Enhancements

### Event Scheduler (Optional)
Automatic random event triggering:
```python
class EventScheduler:
    def __init__(self, game: GameSession):
        self.game = game
        self.last_event_time = None
    
    def should_trigger_event(self) -> bool:
        """Check if random event should trigger"""
        if not self.last_event_time:
            return False
        
        # Minimum 3-5 food tax cycles between events
        cycles_since = self._calculate_cycles_since_last()
        return cycles_since >= random.randint(3, 5)
    
    def select_random_event(self) -> Tuple[str, int]:
        """Select event type and severity based on game progress"""
        progress = self._calculate_game_progress()
        
        if progress < 0.25:  # Early game
            severity = random.randint(1, 2)
        elif progress < 0.75:  # Mid game
            severity = random.randint(2, 3)
        else:  # Late game
            severity = random.randint(3, 5)
        
        event_type = random.choice(list(EventType))
        return event_type, severity
```

### Event Chains
One event triggers another:
```python
event_chains = {
    EventType.EARTHQUAKE: [
        (EventType.FIRE, 0.3),  # 30% chance of fire after earthquake
    ],
    EventType.DROUGHT: [
        (EventType.FAMINE, 0.5),  # 50% chance of famine during drought
    ]
}
```

### Event Modifiers
Scenario-specific event modifications:
```json
{
  "space_race": {
    "event_modifiers": {
      "automation_breakthrough": {
        "bonus_multiplier": 2.0,
        "cost_multiplier": 0.5
      }
    }
  }
}
```

---

## Troubleshooting

### Event Not Triggering
**Symptom**: API call succeeds but no effect seen

**Solutions**:
1. Check game status is `IN_PROGRESS`
2. Verify event type spelling matches `EventType` enum
3. Check severity is 1-5
4. Look for errors in backend logs

### Duration Not Decrementing
**Symptom**: Event stays active indefinitely

**Solutions**:
1. Verify `process_food_tax_cycle()` is called
2. Check `active_events` in game state
3. Ensure `flag_modified(game, 'game_state')` called
4. Check food tax is actually being applied

### Mitigation Not Working
**Symptom**: Buildings don't reduce event impact

**Solutions**:
1. Verify mitigation buildings exist in team state
2. Check building counts (max 5)
3. Ensure correct building type for event:
   - Infrastructure: Earthquake, Drought, Tornado, Recession
   - Hospital: Fire, Plague
   - Restaurant: Blizzard, Recession (currency benefit)

### Plague Not Spreading
**Symptom**: Plague doesn't spread during trades

**Solutions**:
1. Check trade logic checks infection status
2. Verify `infected_teams` list in game state
3. Ensure trade modal blocks infected trades
4. Check WebSocket events for infection updates

---

## Performance Considerations

### Database Queries
- Events stored in both database and game state
- Database for persistence and history
- Game state for fast access during gameplay

### Event Processing
- `process_food_tax_cycle()` runs once per tax cycle
- Processes all active events in single transaction
- Batch updates to database

### WebSocket Broadcasting
- Single broadcast per event trigger
- All players receive same event data
- No per-team filtering needed

---

## See Also

- [EVENT_SYSTEM.md](EVENT_SYSTEM.md) - User-facing documentation
- [FEATURE-FOOD-TAX-AUTOMATION.md](FEATURE-FOOD-TAX-AUTOMATION.md) - Food tax integration
- [CHALLENGE_SYSTEM_README.md](CHALLENGE_SYSTEM_README.md) - Challenge system
- [TRADING_FEATURE_README.md](TRADING_FEATURE_README.md) - Trading system
