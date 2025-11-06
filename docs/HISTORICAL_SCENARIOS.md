# Historical Scenarios Feature

## Overview

The Trading Game now includes 6 historical scenarios that hosts can choose when creating a game. Each scenario provides themed nations, starting resources, special rules, and victory conditions based on real historical events.

## Available Scenarios

### 1. Post-WWII Marshall Plan (1948-1952)
- **Difficulty**: Medium
- **Duration**: 90-120 minutes
- **Description**: Four European nations compete to rebuild after WWII using American aid. Teams must balance infrastructure development, industrial production, and maintaining food security.

**Nations**:
- **Britain**: Strong starting infrastructure, moderate resources
- **France**: Agricultural strength, needs industrial development
- **West Germany**: Industrial potential, low starting resources
- **Italy**: Balanced but resource-poor, must trade aggressively

**Special Rules**:
- Marshall Aid Rounds: Banker distributes bonus currency every 20 minutes (decreasing amounts)
- Cold War Effect: Teams can form trading blocs
- Food Crisis: If any nation drops below food threshold, ALL nations lose 10% currency

**Victory Conditions**:
- First to build 8 buildings (infrastructure-heavy recovery)
- Highest combined infrastructure + medical goods at time limit

---

### 2. Silk Road Trade Routes (200 BCE - 1400 CE)
- **Difficulty**: Easy (great for beginners)
- **Duration**: 90 minutes
- **Description**: Four merchant nations compete along the ancient Silk Road. Success requires smart trading, diverse production, and adapting to changing demand.

**Nations**:
- **China**: Raw materials abundance, electrical goods (silk/porcelain analog)
- **Persia**: Central trading hub, balanced resources
- **Arabia**: Food and medical goods (spices/perfumes)
- **Rome**: Currency-rich, resource-poor (must trade)

**Special Rules**:
- Trading Caravans: Trades take 2 minutes to "travel"
- Demand Shifts: Every 15 minutes, Banker announces which resource doubles in value
- Bandit Raids: Random 10% resource loss events (challenge to prevent)

**Victory Conditions**:
- First to complete 6 buildings across all types (diversification strategy)
- Most total resource volume at time limit

---

### 3. Industrial Revolution Britain (1760-1840)
- **Difficulty**: Hard
- **Duration**: 120 minutes
- **Description**: Four British regions race to industrialize. Teams must balance agricultural base with factory development while managing worker welfare.

**Nations**:
- **Lancashire**: Textile focus (electrical goods = textiles)
- **Yorkshire**: Mining and raw materials
- **Midlands**: Ironworks and infrastructure
- **Scotland**: Agricultural base, late industrializer

**Special Rules**:
- Factory System: Factories produce double output but cost 1 food per production cycle
- Worker Strikes: If medical goods fall below threshold, all factories stop for 5 minutes
- Railway Boom: After 60 minutes, Infrastructure buildings unlock 50% faster trades

**Victory Conditions**:
- First to build 10 factories (any type)
- Highest (buildings × remaining resources) score at time limit

---

### 4. Space Race (1957-1975)
- **Difficulty**: Medium
- **Duration**: 90 minutes
- **Description**: Four space agencies compete to achieve milestones. Technology, infrastructure, and international cooperation determine success.

**Nations**:
- **USA**: High starting currency, balanced production
- **USSR**: Strong raw materials, infrastructure focus
- **Europe**: Collaborative (shared resources with one ally)
- **China**: Late starter, faster production after first building

**Special Rules**:
- Research Milestones: First team to build each building type earns bonus currency
- Satellite Network: Teams with 3+ Infrastructure buildings can "spy" on others' resources
- Moon Race: Final 20 minutes, all building costs increase 50%

**Victory Conditions**:
- First to build 3 Medical Factories (advanced technology)
- Most diverse portfolio (all 8 building types) at time limit

---

### 5. Age of Exploration (1492-1600)
- **Difficulty**: Medium
- **Duration**: 90-120 minutes
- **Description**: Four European powers compete to establish colonial trade empires. Discovery, exploitation, and strategic partnerships drive success.

**Nations**:
- **Spain**: Gold-rich (high currency), low initial production
- **Portugal**: Trade specialists (cheaper exchanges)
- **England**: Naval infrastructure focus
- **Netherlands**: Agricultural and industrial balance

**Special Rules**:
- Discovery Voyages: Teams spend 100 currency + 1 food to attempt discovery (challenge) for resource bonuses
- Colonial Goods: Medical goods and electrical goods worth 2× in trades (luxury goods)
- Piracy Tax: Every 15 minutes, all teams lose 5% resources (challenge to prevent)

**Victory Conditions**:
- First to 800 total currency accumulated
- Highest (buildings + remaining currency) score at time limit

---

### 6. Great Depression Recovery (1929-1939)
- **Difficulty**: Hard
- **Duration**: 90 minutes
- **Description**: Four nations attempt different economic strategies to escape depression. Resource scarcity, trade restrictions, and food insecurity create intense pressure.

**Nations**:
- **USA**: New Deal focus (infrastructure-heavy)
- **Germany**: Industrial rearmament (factory focus)
- **Britain**: Imperial trade preference (trading bloc with one ally)
- **Sweden**: Social democracy (balanced approach)

**Special Rules**:
- Depression Start: All teams begin with 50% normal starting resources
- Trade Barriers: International trades cost 10% tariff (paid to banker)
- Public Works: Infrastructure buildings provide +5% food production
- Bank Runs: Every 20 minutes, all teams must have 100 currency or lose 1 building

**Victory Conditions**:
- First team to reach pre-depression prosperity (1000 total assets)
- Most buildings at time limit (recovery metric)

---

## How to Use Scenarios

### For Hosts

1. **Create a New Game**: Start by creating a game as usual
2. **Open Game Settings**: You'll be taken to the game settings page
3. **Select a Scenario**: Choose from the dropdown under "Historical Scenario (Optional)"
4. **Review Details**: Scenario description, nations, and rules will be displayed
5. **Auto-Configuration**: Selecting a scenario automatically sets:
   - Number of teams (always 4 for scenarios)
   - Game duration (recommended for that scenario)
   - Difficulty level
6. **Start Game**: Proceed to the dashboard and start the game

### Starting Resources

Each scenario has unique starting resources and buildings for each nation. When the game starts:
- Teams are automatically assigned their scenario-specific nation
- Starting resources match the historical theme
- Building counts reflect the nation's strengths

### Special Rules Implementation

**Important**: Special rules provide thematic gameplay guidelines. The system currently automates setup but most special rules require Banker/Host implementation during gameplay.

#### ✅ Fully Automated:
- **Starting Resources**: Each nation automatically receives scenario-specific resources
- **Starting Buildings**: Nations begin with historically appropriate buildings
- **Team Configuration**: Automatically sets 4 teams for all scenarios
- **Game Duration**: Auto-sets recommended duration (can be adjusted)
- **Difficulty Level**: Auto-configures difficulty (Easy/Medium/Hard)

#### ⚠️ Requires Manual Implementation by Banker/Host:
- **Periodic Bonuses**: Marshall Aid distributions, Demand Shifts - Banker must track time and distribute
- **Triggered Penalties**: Food Crisis, Worker Strikes, Bank Runs - Banker monitors conditions and applies
- **Time-based Events**: Railway Boom, Moon Race cost increases - Banker announces at specified times
- **Special Mechanics**: Trading Caravans delays, Spy actions, Discovery Voyages - Players/Banker coordinate
- **Victory Tracking**: Monitor victory conditions throughout the game

#### 🔮 Future Automation:
Future updates will automate more mechanics:
- Automatic periodic bonuses and penalties
- Real-time victory condition tracking
- Timer-based rule triggers
- Automated resource loss/gain events

### Victory Conditions

Victory conditions are guidelines for determining the winner. The Banker should track these metrics throughout the game and announce the winner at the end based on the scenario's victory conditions.

## API Usage

### List Available Scenarios
```bash
GET /scenarios
```

Returns all 6 scenarios with basic information.

### Get Scenario Details
```bash
GET /scenarios/{scenario_id}
```

Returns full details including nation profiles, special rules, and victory conditions.

### Set Game Scenario
```bash
POST /games/{game_code}/set-scenario?scenario_id={scenario_id}
```

Applies a scenario to a game. Must be called before the game starts.

## Technical Details

### Database Schema
- Added `scenario_id` column to `game_sessions` table
- Migration: `002_add_scenario_id_column.sql`

### Backend Files
- `backend/scenarios.py`: Scenario definitions and helper functions
- `backend/main.py`: API endpoints for scenarios
- `backend/game_logic.py`: Integration with game initialization

### Frontend Files
- `frontend/game-settings.html`: Scenario selection UI
- `frontend/dashboard.js`: Display scenario information

### Game State
When a scenario is set, the game_state includes:
```json
{
  "scenario": {
    "id": "silk_road",
    "name": "Silk Road Trade Routes",
    "period": "200 BCE - 1400 CE",
    "special_rules": [...],
    "victory_conditions": [...]
  },
  "teams": {
    "1": {
      "name": "China",
      "description": "Raw materials abundance...",
      "resources": {...},
      "buildings": {...}
    }
  }
}
```

## Future Enhancements

Potential improvements for scenario system:

1. **Automated Special Rules**: Implement periodic bonuses and penalties automatically
2. **Custom Scenarios**: Allow hosts to create and save custom scenarios
3. **More Scenarios**: Add more historical periods (Renaissance, Colonial America, etc.)
4. **Scenario Variations**: Different difficulty variants of each scenario
5. **Victory Tracking**: Automatic victory condition tracking and announcements
6. **Scenario Achievements**: Track player performance across scenarios

## Testing

Unit tests are provided in:
- `backend/tests/test_scenarios.py`: Tests for scenario data structure
- `backend/tests/test_scenario_api.py`: Tests for API endpoints

Run tests:
```bash
cd backend
pytest tests/test_scenarios.py -v
```

## Credits

Scenarios designed based on real historical events to provide educational and engaging gameplay experiences.
