# Building Construction System

## Overview

The Trading Game now includes a comprehensive building construction system that allows teams to build new production and optional buildings by spending resources. Each building has specific costs and optional buildings provide special benefits that enhance gameplay.

## Features

### Building Construction
- Players can build new buildings by spending resources
- Resource costs are validated before construction
- Buildings are added to the team's inventory upon successful construction
- Real-time WebSocket updates notify all team members of new buildings

### Building Types

#### Production Buildings
These buildings produce resources when players complete physical challenges:

- **Farm** - Produces Food
  - Cost: 50 Currency, 30 Raw Materials
  
- **Mine** - Produces Raw Materials  
  - Cost: 50 Currency, 30 Raw Materials, 5 Electrical Goods
  
- **Electrical Factory** - Produces Electrical Goods
  - Cost: 200 Currency, 50 Raw Materials, 30 Electrical Goods
  
- **Medical Factory** - Produces Medical Goods
  - Cost: 200 Currency, 50 Raw Materials, 20 Food, 15 Electrical Goods

#### Optional Buildings
These buildings provide special benefits and have maximum limits:

- **School** - Allows single team member to use factories
  - Cost: 100 Currency, 30 Raw Materials
  - Benefit: Farm and Mine production only requires 1 team member instead of full team. Increases food tax.
  - Limit: Unlimited
  
- **Hospital** - Reduces disease impact
  - Cost: 300 Currency, 50 Raw Materials, 10 Electrical Goods, 10 Medical Goods
  - Benefit: Each hospital reduces disease impact by 20%. Max 5 hospitals = no disease impact.
  - Limit: Maximum 5 per team
  
- **Restaurant** - Generates currency on food tax payment
  - Cost: 200 Currency, 50 Raw Materials, 25 Food, 5 Electrical Goods
  - Benefit: Generates 5 currency per food unit taxed × number of restaurants. Max 5 restaurants.
  - Limit: Maximum 5 per team
  
- **Infrastructure** - Reduces drought impact
  - Cost: 300 Currency, 50 Raw Materials, 10 Electrical Goods
  - Benefit: Each infrastructure reduces drought impact by 20%. Max 5 infrastructure = no drought impact.
  - Limit: Maximum 5 per team

## Special Building Effects

### Restaurant Effect
When food tax is applied to a nation, restaurants generate bonus currency:
- **Formula**: `food_tax_amount × 5 currency × number_of_restaurants`
- **Example**: With 2 restaurants and 15 food tax (developed nation):
  - Currency generated: 15 × 5 × 2 = **150 currency**
- Scales linearly with number of restaurants (1-5)
- Only activates when food tax is successfully paid (not during famine)

### Hospital Effect
When disease strikes a nation, hospitals reduce the medical goods required:
- **Formula**: `base_medical_needed × (1 - hospital_count × 0.2)`
- **Example**: Disease severity 5 (50 medical goods needed) with 3 hospitals:
  - Reduction: 60% (3 × 20%)
  - Medical goods needed: 50 × 0.4 = **20 medical goods**
- At 5 hospitals (100% reduction): **Complete disease immunity**

### Infrastructure Effect
When drought occurs, infrastructure reduces the production impact:
- **Formula**: `drought_severity × (1 - infrastructure_count × 0.2)`
- **Example**: Drought severity 5 with 2 infrastructures:
  - Reduction: 40% (2 × 20%)
  - Effective severity: 5 × 0.6 = **3.0**
- At 5 infrastructures (100% reduction): **Complete drought immunity**

## API Endpoints

### Build Building
```http
POST /games/{game_code}/build-building
Content-Type: application/json

{
    "team_number": 1,
    "building_type": "farm"
}
```

**Success Response (200 OK):**
```json
{
    "success": true,
    "message": "Successfully built farm for Team 1",
    "team_number": 1,
    "building_type": "farm",
    "new_count": 4,
    "remaining_resources": {
        "currency": 50,
        "raw_materials": 20,
        "food": 30
    }
}
```

**Error Responses:**
- `400 Bad Request` - Insufficient resources, invalid building type, or limit reached
- `404 Not Found` - Game not found

### WebSocket Event
When a building is constructed, all clients receive:
```json
{
    "type": "event",
    "event_type": "building_constructed",
    "data": {
        "team_number": 1,
        "building_type": "farm",
        "new_count": 4,
        "resources": {
            "currency": 50,
            "raw_materials": 20,
            "food": 30
        }
    }
}
```

## Frontend Usage

### Building Construction UI
The player dashboard includes a "Build New Buildings" section that displays:
- All buildable buildings with icons and descriptions
- Current count and maximum limit (for optional buildings)
- Resource costs with color-coded availability:
  - Green: Sufficient resources
  - Red: Insufficient resources
- Build button (disabled if resources insufficient or limit reached)

### JavaScript API
```javascript
// Build a building
await gameAPI.buildBuilding(gameCode, teamNumber, buildingType);

// Example
await gameAPI.buildBuilding('ABC123', 1, 'hospital');
```

## Testing

### Manual Testing
Run the comprehensive test suite:
```bash
cd backend
python manual_test_buildings.py
```

This tests:
- Resource cost validation
- Building limits enforcement
- Restaurant currency generation
- Hospital disease reduction
- Infrastructure drought reduction
- Scaling effects with multiple buildings

### Unit Tests
```bash
cd backend
pytest tests/test_building_construction.py -v
pytest tests/test_building_effects.py -v
```

## Game Balance

### Resource Economy
Building costs are designed to:
- Encourage trading between nations
- Create strategic choices between production and optional buildings
- Require significant investment for powerful optional buildings

### Building Limits
Optional buildings are limited to prevent overpowered strategies:
- Maximum 5 hospitals, restaurants, or infrastructures per team
- Provides diminishing returns (20% per building)
- Complete immunity requires full investment (5 buildings)

### Strategic Considerations
- **Early Game**: Focus on production buildings (farms, mines)
- **Mid Game**: Build schools to improve production efficiency
- **Late Game**: Invest in optional buildings for protection and bonuses
- **Trade-offs**: Balance between immediate production and long-term benefits

## Implementation Details

### Backend
- `backend/main.py`: Build building endpoint with validation
- `backend/game_logic.py`: Building construction logic and special effects
- `backend/game_constants.py`: Building costs, limits, and benefits

### Frontend
- `frontend/game-api.js`: API client method
- `frontend/dashboard.js`: Building UI and event handling
- `frontend/dashboard-styles.css`: Building card styling

## Future Enhancements

Potential improvements:
1. Building upgrades (increase production/effects)
2. Building maintenance costs
3. Building destruction events
4. Unique nation-specific buildings
5. Building trade between nations
6. Visual indicators for building effects in action

## Known Issues

- FastAPI/Pydantic compatibility issue prevents full API integration tests
  - Workaround: Manual test script validates all functionality
  - Fix: Upgrade FastAPI to version >=0.110.0 (requires stable network connection)

## References

- Original issue: "Create process to build new buildings"
- Game rules: `QUICKSTART.md`
- Challenge system: `CHALLENGE_SYSTEM_README.md`
