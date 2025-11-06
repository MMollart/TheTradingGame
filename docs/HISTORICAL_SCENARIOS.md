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

Detailed roadmap for automating and expanding the scenario system:

### Phase 1: Core Automation (High Priority)

#### 1.1 Automated Periodic Events
**Goal**: Automatically trigger time-based bonuses and penalties without manual intervention.

**Implementation**:
- Create `ScenarioEventScheduler` service similar to `food_tax_scheduler.py`
- Store event timers in game_state with pause-aware tracking
- WebSocket broadcasts when events trigger

**Example Events**:
- **Marshall Aid** (Marshall Plan): Auto-distribute currency at 20, 40, 60 min marks
- **Demand Shifts** (Silk Road): Auto-select and announce doubled resource every 15 min
- **Piracy Tax** (Age of Exploration): Auto-deduct 5% resources every 15 min
- **Bank Runs** (Great Depression): Auto-check currency threshold every 20 min

**Technical Approach**:
```python
# backend/scenario_event_scheduler.py
class ScenarioEventScheduler:
    def schedule_scenario_events(self, game_code: str, scenario_id: str):
        scenario = get_scenario(scenario_id)
        for rule in scenario["special_rules"]:
            if rule["implementation"] == "periodic_event":
                self.create_timer(game_code, rule)
```

**User Story**: _"As a Banker, I want periodic events to happen automatically so I can focus on player interactions instead of watching the clock."_

#### 1.2 Real-time Victory Tracking
**Goal**: Automatically track victory conditions and notify when teams achieve milestones.

**Implementation**:
- Add `VictoryTracker` class that monitors game_state changes
- Dashboard widget showing progress toward victory conditions
- WebSocket event when victory condition met

**Example Tracking**:
- Building counts for "First to 8 buildings"
- Resource totals for "First to 800 currency"
- Building type diversity for "All 8 building types"

**Technical Approach**:
```python
# backend/victory_tracker.py
class VictoryTracker:
    def check_victory_conditions(self, game: GameSession):
        scenario = game.game_state.get("scenario")
        for condition in scenario["victory_conditions"]:
            if condition["type"] == "buildings_count":
                self.check_building_count(game, condition)
```

**User Story**: _"As a Host, I want to see real-time progress toward victory conditions so I can build excitement as teams get close to winning."_

#### 1.3 Automated Resource Events
**Goal**: Automatically apply resource gains/losses from scenario events.

**Implementation**:
- Integrate with challenge system for prevention mechanics
- Random event generator for unpredictable events
- Resource change animations in UI

**Example Events**:
- **Bandit Raids** (Silk Road): Random team loses 10% resources
- **Discovery Voyages** (Age of Exploration): Bonus resources on challenge completion
- **Food Crisis** (Marshall Plan): All teams lose 10% currency when triggered

**Technical Approach**:
```python
# In game_logic.py
def apply_scenario_resource_event(game, team_number, event_type):
    if event_type == "bandit_raid":
        resources = game.game_state["teams"][str(team_number)]["resources"]
        for resource in resources:
            resources[resource] = int(resources[resource] * 0.9)
```

**User Story**: _"As a Player, I want random events to feel impactful and fair, with clear notifications of what happened and why."_

---

### Phase 2: Enhanced Mechanics (Medium Priority)

#### 2.1 Conditional Rule Triggers
**Goal**: Automatically detect and apply rules based on game conditions.

**Implementation**:
- Condition monitoring service checks thresholds every minute
- Automatic penalty/bonus application
- Notification system for triggered rules

**Example Triggers**:
- **Food Crisis** (Marshall Plan): Monitor all teams' food levels, trigger penalty when any drops below 10
- **Worker Strikes** (Industrial Revolution): Detect medical goods < 5, pause factory production for 5 minutes
- **Moon Race** (Space Race): At 70-minute mark, increase all building costs by 50%

**Technical Approach**:
```python
# backend/scenario_conditions.py
class ScenarioConditionMonitor:
    def check_conditions(self, game: GameSession):
        scenario = game.game_state.get("scenario")
        for rule in scenario["special_rules"]:
            if rule["implementation"] == "penalty_trigger":
                self.evaluate_trigger(game, rule)
```

**User Story**: _"As a team, we want to know immediately when we trigger scenario conditions so we can adjust our strategy."_

#### 2.2 Trading Delays & Mechanics
**Goal**: Implement scenario-specific trading rules automatically.

**Implementation**:
- Extend trading system with delay queues
- Tariff/multiplier system for resource values
- Trading bloc formation UI

**Example Mechanics**:
- **Trading Caravans** (Silk Road): 2-minute delay before trade completes
- **Trade Barriers** (Great Depression): 10% tariff auto-deducted and sent to banker
- **Colonial Goods** (Age of Exploration): 2× value for medical/electrical in trades
- **Cold War Blocs** (Marshall Plan): Shared resource pools for allied teams

**Technical Approach**:
```python
# In trading_api.py
def apply_scenario_trade_rules(trade, scenario):
    if "trade_delay" in scenario["special_rules"]:
        trade.completion_time = datetime.now() + timedelta(minutes=2)
    if "tariff_percent" in scenario["special_rules"]:
        tariff = calculate_tariff(trade.resources, scenario)
        deduct_tariff(trade, tariff)
```

**User Story**: _"As a trader, I want scenario-specific trading rules to be enforced automatically so I can't accidentally violate the historical theme."_

#### 2.3 Special Building Effects
**Goal**: Automate scenario-specific building bonuses and effects.

**Implementation**:
- Building effect calculator integrated with production system
- Visual indicators for active building effects
- Stacking rules for multiple buildings

**Example Effects**:
- **Factory System** (Industrial Revolution): Factories auto-consume 1 food per production, double output
- **Public Works** (Great Depression): Infrastructure auto-adds 5% to food production
- **Research Milestones** (Space Race): First builder of each type auto-receives 50 currency
- **Railway Boom** (Industrial Revolution): After 60 min, infrastructure buildings reduce trade time by 50%

**Technical Approach**:
```python
# In game_logic.py
def calculate_production_with_scenario(building_type, team_state, scenario):
    base_production = BUILDING_PRODUCTION[building_type]["amount"]
    if scenario["id"] == "industrial_revolution":
        multiplier = 2
        food_cost = 1
        return base_production * multiplier, {"food": food_cost}
```

**User Story**: _"As a team, we want our buildings to automatically provide scenario-specific benefits so we can focus on strategy rather than manual calculations."_

---

### Phase 3: Advanced Features (Low Priority)

#### 3.1 Custom Scenario Builder
**Goal**: Allow hosts to create and save custom scenarios with a visual editor.

**Implementation**:
- Scenario editor UI with drag-and-drop nation builder
- Template library based on existing scenarios
- JSON export/import for sharing
- Database storage for saved custom scenarios

**Features**:
- Nation profile creator (name, description, starting resources/buildings)
- Special rules selector from predefined list
- Victory condition builder with multiple options
- Scenario preview and test mode

**Technical Approach**:
```python
# New model in models.py
class CustomScenario(Base):
    __tablename__ = "custom_scenarios"
    id = Column(Integer, primary_key=True)
    creator_user_id = Column(Integer, ForeignKey("users.id"))
    scenario_name = Column(String(100))
    scenario_data = Column(JSON)  # Full scenario definition
    is_public = Column(Boolean, default=False)
```

**User Story**: _"As a creative Host, I want to design my own historical scenarios so I can teach my group about any period in history."_

#### 3.2 Scenario Achievements & Stats
**Goal**: Track player performance across scenarios with achievements and leaderboards.

**Implementation**:
- Achievement system for scenario-specific goals
- Player scenario stats (wins, fastest victory, etc.)
- Leaderboard per scenario
- Achievement badges displayed on player profile

**Example Achievements**:
- "Marshall Plan Champion": Win Marshall Plan 3 times
- "Silk Road Master": Complete 6 diverse buildings in Silk Road
- "Industrial Tycoon": Build 10 factories in Industrial Revolution
- "Space Pioneer": Achieve all 3 victory conditions in Space Race

**Technical Approach**:
```python
# backend/models.py
class ScenarioAchievement(Base):
    __tablename__ = "scenario_achievements"
    player_id = Column(Integer, ForeignKey("players.id"))
    scenario_id = Column(String(50))
    achievement_type = Column(String(50))
    unlocked_at = Column(DateTime)
```

**User Story**: _"As a competitive Player, I want to earn achievements and see my ranking on leaderboards so I can prove my mastery of each scenario."_

#### 3.3 Scenario Variations & Difficulty Modes
**Goal**: Generate alternate versions of scenarios with adjusted parameters.

**Implementation**:
- Difficulty multiplier system for resources/costs
- Random event frequency adjustments
- Victory condition variations
- "Remix" mode with randomized rules

**Example Variations**:
- **Silk Road: Beginner Mode**: No bandit raids, longer demand shift intervals
- **Industrial Revolution: Expert Mode**: Worker strikes at 10 medical goods instead of 5, double food cost for factories
- **Space Race: Co-op Mode**: Teams can share milestone bonuses
- **Marshall Plan: Speed Run**: Half duration, double Marshall Aid amounts

**Technical Approach**:
```python
# In scenarios.py
def generate_scenario_variation(base_scenario, difficulty_mode):
    modified = copy.deepcopy(base_scenario)
    if difficulty_mode == "beginner":
        modified["starting_resources"] = {k: int(v * 1.5) for k, v in modified["starting_resources"].items()}
    return modified
```

**User Story**: _"As a returning Player, I want to experience familiar scenarios with new twists so the game stays fresh and challenging."_

#### 3.4 More Historical Scenarios
**Goal**: Expand to 15-20 total scenarios covering major historical periods.

**Proposed Additional Scenarios**:
1. **Renaissance Italy** (1400-1600) - City-state competition, art patronage
2. **American Colonial Period** (1607-1776) - Settling, trade with natives, independence
3. **Viking Age Trade** (793-1066) - Raids, exploration, trade routes
4. **Chinese Dynasties** (Various) - Imperial expansion, silk monopoly
5. **African Kingdoms** (1000-1500) - Gold trade, Saharan caravans
6. **Japanese Modernization** (1868-1912) - Meiji restoration, industrialization
7. **Cold War Proxy Wars** (1947-1991) - Resource control, alliances
8. **Roaring Twenties** (1920-1929) - Economic boom before depression
9. **Green Revolution** (1960-2000) - Agricultural technology race
10. **Digital Age** (1990-2020) - Technology companies, startup ecosystem

**Implementation Priority**: Add 2-3 new scenarios per quarter based on player demand.

**User Story**: _"As an educator, I want scenarios covering diverse historical periods so I can use the game to teach about any era relevant to my curriculum."_

---

### Phase 4: Integration & Polish (Ongoing)

#### 4.1 Tutorial Mode for Scenarios
- Guided walkthrough of scenario mechanics
- Practice mode with AI opponents
- Scenario-specific tips and strategy hints

#### 4.2 Scenario Analytics Dashboard
- Host view of team progress and strategies
- Historical data on winning strategies per scenario
- Balance analysis to identify if scenarios favor certain playstyles

#### 4.3 Mobile-Friendly Scenario Selection
- Responsive design for scenario browser
- Scenario preview cards with images
- Quick-play mode for popular scenarios

#### 4.4 Multilingual Scenario Support
- Translations for scenario names and descriptions
- Localized nation names where appropriate
- Cultural notes and educational content

---

### Implementation Timeline (Estimated)

**Quarter 1**: Phase 1 (Core Automation)
- Automated periodic events
- Real-time victory tracking
- Automated resource events

**Quarter 2**: Phase 2 (Enhanced Mechanics)
- Conditional rule triggers
- Trading delays & mechanics
- Special building effects

**Quarter 3**: Phase 3.1-3.2 (Advanced Features Part 1)
- Custom scenario builder
- Scenario achievements & stats

**Quarter 4**: Phase 3.3-3.4 (Advanced Features Part 2)
- Scenario variations
- 3-5 new historical scenarios

**Ongoing**: Phase 4 (Integration & Polish)
- Tutorial mode
- Analytics
- Mobile optimization
- Translations

---

### Contributing to Future Development

Interested in helping implement these features? Check our contribution guidelines:

1. **For Developers**: See `CONTRIBUTING.md` for technical setup
2. **For Educators**: Suggest new scenarios via GitHub Discussions
3. **For Players**: Report bugs and suggest improvements via Issues
4. **For Historians**: Help us ensure historical accuracy of scenarios

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
