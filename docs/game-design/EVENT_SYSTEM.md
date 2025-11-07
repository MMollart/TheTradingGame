# Game Events System

Complete guide to the expanded game events system in The Trading Game, including natural disasters, economic events, and positive events with difficulty scaling and mitigation mechanics.

## Overview

The game events system adds dynamic challenges and opportunities to gameplay through:

- **8 Event Types**: Natural disasters, economic crises, and positive breakthroughs
- **Difficulty Scaling**: Events scale with game difficulty (Easy: 0.75x, Normal: 1.0x, Hard: 1.5x)
- **Severity Levels**: 1-5 severity for fine-tuned event impact
- **Mitigation Mechanics**: Optional buildings reduce event impact
- **Duration Tracking**: Events tracked by food tax cycles
- **Real-time Updates**: WebSocket broadcasts for instant team notifications

## Event Categories

### Natural Disasters
Random events that challenge teams through destruction and production penalties.

### Economic Events
Market-based events affecting prices and costs.

### Positive Events
Opportunities for teams to gain advantages through investment.

---

## Event Types

### 🏚️ Earthquake

**Category**: Natural Disaster  
**Duration**: Instant (permanent destruction)

**Impact**:
- Destroys random buildings from all teams
- Buildings destroyed = `Severity × Difficulty Modifier`
- Maximum 5 buildings per team (hard cap)

**Scaling Examples**:
| Difficulty | Severity | Buildings Destroyed |
|------------|----------|---------------------|
| Easy       | 3        | 2 (3 × 0.75)        |
| Normal     | 3        | 3 (3 × 1.0)         |
| Hard       | 5        | 5 (capped)          |

**Mitigation**:
- Each **Infrastructure** building reduces destruction by 20%
- 5 infrastructure = 100% protection

**API**:
```bash
POST /api/v2/events/games/{game_code}/trigger
{
  "event_type": "earthquake",
  "severity": 3
}
```

---

### 🔥 Fire

**Category**: Natural Disaster  
**Duration**: Instant (permanent destruction)

**Impact**:
- Destroys electrical factories across all teams
- Destruction rate = `20% × Severity × Difficulty Modifier`
- Only affects electrical factories

**Scaling Examples**:
| Difficulty | Severity | % Destroyed | 5 Factories → |
|------------|----------|-------------|---------------|
| Easy       | 2        | 30%         | 1 destroyed   |
| Normal     | 3        | 60%         | 3 destroyed   |
| Hard       | 4        | 120% (100%) | All destroyed |

**Mitigation**:
- Each **Hospital** reduces destruction by 20%
- 5 hospitals = 100% protection

**API**:
```bash
POST /api/v2/events/games/{game_code}/trigger
{
  "event_type": "fire",
  "severity": 3
}
```

---

### 💧 Drought

**Category**: Natural Disaster  
**Duration**: 2 food tax cycles

**Impact**:
- Reduces farm AND mine production
- Production modifier = `0.5 + (3 - Severity) × 0.1`
  - Severity 1-2: Less severe (60% production)
  - Severity 3: Standard (50% production)
  - Severity 4-5: More severe (40-30% production)

**Scaling Examples**:
| Difficulty | Severity | Production | 10 Food/Cycle → |
|------------|----------|------------|-----------------|
| Easy       | 2        | 60%        | 6 food          |
| Normal     | 3        | 50%        | 5 food          |
| Hard       | 5        | 30%        | 3 food          |

**Mitigation**:
- Each **Infrastructure** reduces penalty by 20%
- Example: 50% penalty with 2 infrastructure → 70% production

**Duration**:
- Tracked by food tax cycles
- Automatically expires after 2 cycles

**API**:
```bash
POST /api/v2/events/games/{game_code}/trigger
{
  "event_type": "drought",
  "severity": 3
}
```

---

### 🦠 Plague

**Category**: Natural Disaster (Contagious)  
**Duration**: Until cured

**Impact**:
- Reduces ALL production by `30% × Severity × Difficulty Modifier`
- Starts with 1-2 randomly infected teams
- **Spreads during trades** between infected and non-infected teams
- Infected teams **cannot trade** with non-infected teams

**Production Penalty Examples**:
| Difficulty | Severity | Penalty | 10 Food/Cycle → |
|------------|----------|---------|-----------------|
| Easy       | 2        | 45%     | 5.5 food        |
| Normal     | 3        | 90%     | 1 food          |
| Hard       | 5        | 225%*   | 0 food          |

*Capped at 100%

**Mitigation**:
- Each **Hospital** reduces penalty by 20%
- Example: 90% penalty with 3 hospitals → 36% penalty

**Cure**:
- Teams pay medicine to bank: `5 × Difficulty Modifier`
  - Easy: 4 medicine
  - Normal: 5 medicine
  - Hard: 8 medicine
- Cured teams removed from infection list

**Contagion Rules**:
1. Infected teams cannot initiate trades with non-infected teams
2. Any trade between infected/non-infected spreads plague
3. Banker is immune (can trade with infected teams)
4. Display infection status prominently in UI

**API**:
```bash
# Trigger plague
POST /api/v2/events/games/{game_code}/trigger
{
  "event_type": "plague",
  "severity": 3
}

# Cure plague
POST /api/v2/events/games/{game_code}/cure-plague
{
  "team_number": "1"
}
```

---

### ❄️ Blizzard

**Category**: Natural Disaster  
**Duration**: 2 food tax cycles

**Impact**:

**Food Tax Increase**:
- Food tax multiplied by `2.0 × Severity × Difficulty Modifier`
- Example: Normal difficulty, Severity 3 = ×6 food tax

**Production Decrease**:
- Easy: -10% (0.9 multiplier)
- Normal: -20% (0.8 multiplier)
- Hard: -30% (0.7 multiplier)
- Affects ALL production buildings

**Scaling Examples**:
| Difficulty | Severity | Food Tax Mult. | Production |
|------------|----------|----------------|------------|
| Easy       | 2        | ×3             | 90%        |
| Normal     | 3        | ×6             | 80%        |
| Hard       | 4        | ×12            | 70%        |

**Mitigation**:
- **Restaurants**: Generate currency rebate (20% of food tax per restaurant)
- **Infrastructure**: Reduces production penalty by 10% per building

**API**:
```bash
POST /api/v2/events/games/{game_code}/trigger
{
  "event_type": "blizzard",
  "severity": 3
}
```

---

### 🌪️ Tornado

**Category**: Natural Disaster  
**Duration**: Instant (permanent loss)

**Impact**:
- Removes `15% × Severity × Difficulty Modifier` of ALL resources
- Affects: food, currency, raw materials, electrical goods, medical goods
- Applied equally across all resource types

**Scaling Examples**:
| Difficulty | Severity | % Lost | 100 of each → |
|------------|----------|--------|---------------|
| Easy       | 2        | 22.5%  | Lose 22-23    |
| Normal     | 3        | 45%    | Lose 45       |
| Hard       | 5        | 112%*  | Lose all      |

*Capped at 100%

**Mitigation**:
- Each **Infrastructure** reduces loss by 20%
- Example: 45% loss with 2 infrastructure → 27% loss

**API**:
```bash
POST /api/v2/events/games/{game_code}/trigger
{
  "event_type": "tornado",
  "severity": 3
}
```

---

### 📉 Economic Recession

**Category**: Economic Event  
**Duration**: 2-4 food tax cycles

**Impact**:

**Bank Price Increase**:
- All bank prices increase by `50% × Severity × Difficulty Modifier`

**Building Cost Increase**:
- All building costs increase by `25% × Severity × Difficulty Modifier`

**Duration**:
- Base: 2 cycles
- Formula: `2 + (Severity - 3)` cycles
  - Severity 1: 0 cycles (event doesn't trigger)
  - Severity 2: 1 cycle
  - Severity 3: 2 cycles
  - Severity 4: 3 cycles
  - Severity 5: 4 cycles

**Scaling Examples**:
| Difficulty | Severity | Bank Prices | Building Costs | Duration |
|------------|----------|-------------|----------------|----------|
| Easy       | 2        | +75%        | +37.5%         | 1 cycle  |
| Normal     | 3        | +150%       | +75%           | 2 cycles |
| Hard       | 5        | +375%       | +187%          | 4 cycles |

**Mitigation**:
- Each **Infrastructure** reduces price increases by 20%

**Rewards**:
- Each **Restaurant** generates `50 × Severity × Difficulty Modifier` currency per cycle

**API**:
```bash
POST /api/v2/events/games/{game_code}/trigger
{
  "event_type": "economic_recession",
  "severity": 3
}
```

---

### 🤖 Automation Breakthrough

**Category**: Positive Event  
**Duration**: 2 food tax cycles (after payment)

**Impact**:
- Selected team's factories produce `+50% × Severity × Difficulty Modifier`
- Applies to electrical AND medical factories
- **Requires payment**: `30 × Difficulty Modifier` electrical goods

**Scaling Examples**:
| Difficulty | Severity | Bonus | Cost (E. Goods) | 10 Goods/Cycle → |
|------------|----------|-------|-----------------|------------------|
| Easy       | 2        | +75%  | 22              | 17.5 goods       |
| Normal     | 3        | +150% | 30              | 25 goods         |
| Hard       | 5        | +375% | 45              | 47.5 goods       |

**Selection**:
- **Option 1**: Random team
- **Option 2**: Team with most factories (current implementation)
- **Option 3**: Weighted random (more factories = higher chance)

**Payment Deadline**:
- Must pay within 1 food tax cycle
- If not paid: Bonus forfeited, event ends

**API**:
```bash
# Offer automation breakthrough
POST /api/v2/events/games/{game_code}/trigger
{
  "event_type": "automation_breakthrough",
  "severity": 3,
  "target_team": "2"  # Optional
}

# Complete payment
POST /api/v2/events/games/{game_code}/complete-automation
{
  "team_number": "2"
}
```

---

## Difficulty Scaling

All events use a difficulty modifier:

| Difficulty | Modifier | Effect                     |
|------------|----------|----------------------------|
| Easy       | 0.75x    | 25% less impact            |
| Normal     | 1.0x     | Standard impact            |
| Hard       | 1.5x     | 50% more impact            |

**Formula**: `Final Effect = Base Effect × Severity × Difficulty Modifier`

---

## Severity Guidelines

| Severity | Name     | Impact                  | Recommended Use             |
|----------|----------|-------------------------|-----------------------------|
| 1        | Minor    | Minimal impact          | Tutorial/introduction       |
| 2        | Low      | Manageable impact       | Learning mechanics          |
| 3        | Standard | Significant impact      | Normal gameplay             |
| 4        | High     | Major impact            | Mid-late game drama         |
| 5        | Severe   | Extreme impact          | Late game climactic moments |

---

## Mitigation Buildings

### Infrastructure
- **Max**: 5 buildings
- **Effect**: 20% reduction per building
- **Protects Against**: Earthquake, Drought, Tornado, Economic Recession

### Hospital
- **Max**: 5 buildings
- **Effect**: 20% reduction per building
- **Protects Against**: Fire, Plague

### Restaurant
- **Max**: 5 buildings
- **Effect**: Bonus currency during events
- **Benefits During**: Blizzard, Economic Recession

---

## Event Scheduling Best Practices

### Frequency
- **Minimum**: 3-5 food tax cycles between major events
- **Maximum**: No more than one major event active at a time

### Progression
1. **Early Game** (0-25% elapsed):
   - Severity 1-2 events
   - Introduce mechanics gradually
   
2. **Mid Game** (25-75% elapsed):
   - Severity 3 events
   - Create strategic decisions
   
3. **Late Game** (75-100% elapsed):
   - Severity 4-5 events
   - Dramatic finishes

### Recovery Events
- Use positive events (Automation Breakthrough) after major disasters
- Helps teams recover and maintains engagement

### Dangerous Combinations
Avoid triggering these simultaneously:
- **Plague + Blizzard**: Potential softlock (severe production penalties)
- **Recession + Drought**: Extreme resource shortage
- **Multiple Disasters**: Too punishing, reduces fun

---

## API Reference

### Trigger Event
```http
POST /api/v2/events/games/{game_code}/trigger
Content-Type: application/json

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
  "message": "🏚️ Earthquake! Buildings destroyed across all nations. Severity: 3",
  "event_id": 123,
  "event_data": {
    "affected_teams": [...],
    "total_buildings_destroyed": 8,
    "difficulty_modifier": 1.0
  }
}
```

### Get Active Events
```http
GET /api/v2/events/games/{game_code}/active
```

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

### Cure Plague
```http
POST /api/v2/events/games/{game_code}/cure-plague
Content-Type: application/json

{
  "team_number": "1"
}
```

### Complete Automation Breakthrough
```http
POST /api/v2/events/games/{game_code}/complete-automation
Content-Type: application/json

{
  "team_number": "2"
}
```

---

## WebSocket Events

Events broadcast to all players in real-time:

```javascript
{
  "type": "event",
  "event_type": "game_event_triggered",
  "data": {
    "event_id": 123,
    "event_type": "earthquake",
    "category": "natural_disaster",
    "severity": 3,
    "message": "🏚️ Earthquake! Buildings destroyed across all nations. Severity: 3",
    "event_data": {...}
  }
}
```

**Event Types**:
- `game_event_triggered`: New event started
- `plague_cured`: Team cured of plague
- `automation_activated`: Automation breakthrough activated

---

## Implementation Examples

### Python Backend

```python
from event_manager import EventManager

# Trigger earthquake
event_mgr = EventManager(db)
event = event_mgr.trigger_earthquake(game, severity=3)

# Process food tax cycle (updates event durations)
event_mgr.process_food_tax_cycle(game)

# Get active events
active_events = event_mgr.get_active_events(game)
```

### JavaScript Frontend

```javascript
// Listen for event broadcasts
gameWS.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  
  if (data.event_type === 'game_event_triggered') {
    displayEventNotification(data.data);
    updateActiveEventsList();
  }
});

// Trigger event (host/banker only)
async function triggerEarthquake(severity) {
  const response = await fetch(`/api/v2/events/games/${gameCode}/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event_type: 'earthquake',
      severity: severity
    })
  });
  
  const result = await response.json();
  console.log(result.message);
}
```

---

## Testing

Comprehensive test suite covering all event types:

```bash
# Run event system tests
cd backend
pytest tests/test_event_system.py -v

# Run specific test
pytest tests/test_event_system.py::TestEarthquakeEvent -v
```

**Test Coverage**:
- Difficulty modifiers
- Mitigation multipliers
- Event triggering and effects
- Duration tracking
- API endpoints
- Cure and completion flows

---

## Configuration

Event configuration stored in `backend/event_config.json`:

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
      "mitigation": {
        "infrastructure": {
          "reduction_per_building": 0.2,
          "max_buildings": 5
        }
      },
      "difficulty_scaling": true
    }
  }
}
```

---

## Troubleshooting

### Event Not Triggering
- Check game status is `IN_PROGRESS`
- Verify event type spelling
- Check severity range (1-5)

### Duration Not Decrementing
- Ensure `process_food_tax_cycle()` called on each food tax
- Check `active_events` in game state
- Verify `flag_modified()` called after updates

### Mitigation Not Working
- Verify mitigation buildings exist in team state
- Check building counts (max 5 per type)
- Ensure correct building type for event

### Plague Not Spreading
- Verify trade logic checks infection status
- Ensure `infected_teams` list updated in game state
- Check trade modal blocking for infected teams

---

## Future Enhancements

Potential additions to the event system:

### New Event Types
- **Heatwave**: Increased food spoilage
- **Tsunami**: Coastal nations only
- **Volcanic Eruption**: Temporary production halt, then bonus
- **Tech Boom**: Electrical goods price spike
- **Medical Crisis**: Medical goods price spike

### Advanced Features
- Event chains (one event triggers another)
- Random event scheduler (automatic triggers)
- Event probability weights
- Team-specific events
- Event modifiers from scenarios

---

## See Also

- [CHALLENGE_SYSTEM_README.md](CHALLENGE_SYSTEM_README.md) - Production challenge system
- [FOOD-TAX-QUICKSTART.md](FOOD-TAX-QUICKSTART.md) - Food tax automation
- [TRADING_FEATURE_README.md](TRADING_FEATURE_README.md) - Trading system
- [BUILDING-CONSTRUCTION-SYSTEM.md](BUILDING-CONSTRUCTION-SYSTEM.md) - Building mechanics
