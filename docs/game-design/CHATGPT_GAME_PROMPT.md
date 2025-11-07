# The Trading Game - Game Description Prompt

Use this prompt when asking ChatGPT for help with The Trading Game.

---

## Game Overview

**The Trading Game** is a multiplayer economic simulation where teams compete to build thriving nations through resource management, production, trading, and strategic decision-making. The game is played in real-time with a fixed duration (typically 90-120 minutes).

## Core Mechanics

### Roles
- **Host**: Manages the game, assigns teams, triggers events, oversees gameplay
- **Banker**: Controls bank prices, facilitates trades, manages events (optional role)
- **Players**: Form teams representing nations, manage resources and production

### Teams (Nations)
- 3-6 teams typically (configurable)
- Each team has a custom name (e.g., "Dragon Nation", "Team Phoenix")
- Teams can have 1-6 players
- Players within a team share resources and buildings

### Resources
There are 5 core resource types:
1. **Food** - Consumed by food tax, required for medical factories
2. **Currency** - Used to purchase resources from bank and build buildings
3. **Raw Materials** - Base production resource, required for all buildings
4. **Electrical Goods** - Advanced resource, required for complex buildings
5. **Medical Goods** - Healthcare resource, required for hospitals

### Buildings

**Production Buildings** (generate resources):
- **Farm** - Produces Food (5 per cycle)
- **Mine** - Produces Raw Materials (5 per cycle)
- **Electrical Factory** - Produces Electrical Goods (5 per cycle, requires 5 raw materials input)
- **Medical Factory** - Produces Medical Goods (5 per cycle, requires 5 food input)

**Service Buildings** (provide bonuses):
- **School** - Allows individual team members to produce independently (increases food tax)
- **Hospital** - Reduces disease/plague impact by 20% per hospital (max 5)
- **Restaurant** - Generates currency during food tax and economic events (max 5)
- **Infrastructure** - Reduces disaster impact by 20% per building (max 5)

**Building Costs** (example for Farm):
- 50 Currency + 30 Raw Materials = 1 Farm

All buildings require resources to build. More advanced buildings cost more.

### Production System

**Challenge-Based Production**:
1. Player requests a challenge from banker/host for a specific building
2. Banker/host assigns a physical challenge (e.g., "20 push-ups", "30 seconds plank")
3. Player completes the challenge in real life
4. Banker approves completion → Player receives production grant

**School Mechanic**:
- Without School: **One challenge locks entire team** (all buildings unavailable)
- With School: **Individual challenges per player** (team can produce from multiple buildings simultaneously)
- Trade-off: School increases food tax consumption

**Production Grants** (per successful challenge):
- Farm → +5 Food
- Mine → +5 Raw Materials
- Electrical Factory → +5 Electrical Goods (costs 5 raw materials)
- Medical Factory → +5 Medical Goods (costs 5 food)

### Food Tax System

**Automatic Tax Cycles**:
- Triggers every 30 seconds (configurable)
- Each team pays food based on number of players and schools
- Base food tax: `2 food per player`
- School penalty: `+1 food per school` (total team)
- Example: 4 players + 2 schools = 10 food per cycle

**Restaurant Benefits**:
- Each restaurant refunds 20% of food tax as currency
- Example: Pay 10 food → Receive 2 currency per restaurant

**Consequences of Non-Payment**:
- If team cannot pay food tax: Currency penalty (-50 to -100 currency, scales with difficulty)
- Repeated failures can cripple a team's economy

### Trading System

**Bank Trading**:
- Banker sets dynamic prices for all resources
- Players can buy/sell resources with currency
- Prices fluctuate based on supply/demand or banker decisions
- Typical prices: 10-30 currency per resource unit

**Team-to-Team Trading**:
- Players can create trade offers (e.g., "Give 20 food for 50 currency")
- Other teams can accept, reject, or counter-offer
- Trades are bilateral (2 teams only)
- No trade fees between teams

### Game Events

Events are triggered by host/banker to create dynamic gameplay:

**Natural Disasters**:
- **Earthquake** - Destroys random buildings
- **Fire** - Destroys electrical factories
- **Drought** - Reduces farm/mine production for 2 cycles
- **Plague** - Contagious disease that spreads via trade, reduces all production
- **Blizzard** - Doubles food tax, reduces production
- **Tornado** - Removes percentage of all resources

**Economic Events**:
- **Economic Recession** - Increases bank prices and building costs
- **Automation Breakthrough** - Selected team gets +50% factory production bonus

**Mitigation**:
- Infrastructure buildings reduce disaster damage
- Hospitals reduce disease/plague effects
- Restaurants provide currency during economic hardship

### Win Conditions

**Scoring** (calculated at game end):
- **Resource Value**: Total resources × assigned values
- **Building Value**: Total buildings × building costs
- **Final Score**: Resource Value + Building Value

Team with highest total score wins.

### Difficulty Levels

- **Easy**: 0.75× effect multiplier (higher production, lower penalties)
- **Normal**: 1.0× effect multiplier (balanced)
- **Hard**: 1.5× effect multiplier (lower production, higher penalties)

Affects:
- Production grants
- Food tax amounts
- Disaster severity
- Event impacts

### Historical Scenarios

The game can use historical settings that modify starting conditions:
- **Industrial Revolution** (1760-1840)
- **Space Race** (1955-1975)
- **World War II** (1939-1945)
- **Age of Exploration** (1400-1600)
- **Renaissance** (1300-1600)
- **Information Age** (1970-present)

Each scenario affects:
- Starting resources
- Available buildings
- Event types
- Victory conditions

### Key Strategic Elements

**Resource Management**:
- Balance production (building factories) vs consumption (food tax)
- Stockpile critical resources for events
- Trade surplus resources for needed ones

**Team Coordination**:
- Decide which buildings to prioritize
- Assign challenges to appropriate team members
- Coordinate production timing with food tax cycles

**Economic Strategy**:
- Buy low from bank when prices are favorable
- Build restaurants early for passive income
- Invest in infrastructure to protect against disasters

**Risk Management**:
- Build hospitals to reduce plague impact
- Maintain food reserves for blizzards
- Diversify production to avoid single points of failure

### Physical Challenge Component

Unlike traditional video games, The Trading Game requires **real-world physical challenges**:
- Encourages movement and exercise during gameplay
- Creates memorable moments (team celebrating after completing challenges)
- Balances digital strategy with physical activity
- Suitable for youth groups, schools, team-building events

**Example Challenge Types**:
- Push-ups (10-30)
- Sit-ups (10-30)
- Burpees (5-20)
- Star Jumps (10-30)
- Squats (10-30)
- Plank (10-60 seconds)
- Jumping Jacks (10-30)

Banker/host can adjust difficulty and quantity based on player age/fitness.

### Technical Implementation

- **Backend**: FastAPI (Python), PostgreSQL database
- **Frontend**: Vanilla JavaScript, HTML/CSS
- **Real-time Communication**: WebSockets for live updates
- **Deployment**: Azure App Service (cloud-hosted)

Players join via web browser using a game code (e.g., "S7YKXM"). No app installation required.

---

## Example Gameplay Flow

1. **Setup (5-10 min)**:
   - Host creates game, gets game code
   - Players join with game code and names
   - Host assigns players to teams
   - Host selects scenario and difficulty

2. **Early Game (0-30 min)**:
   - Teams build initial farms and mines
   - Players complete challenges to stockpile food and raw materials
   - Food tax begins draining food reserves
   - Teams trade with bank to balance resources

3. **Mid Game (30-60 min)**:
   - Teams build advanced factories (electrical, medical)
   - First event triggers (e.g., drought)
   - Teams build service buildings (schools, hospitals, restaurants)
   - Team-to-team trading increases

4. **Late Game (60-90 min)**:
   - Major events occur (plague, economic recession)
   - Teams race to maximize production
   - Strategic trades and resource management critical
   - Timer countdown creates urgency

5. **Game End**:
   - Timer expires or host ends game
   - Final scores calculated
   - Winner announced
   - Teams review stats and performance

---

## Use Cases

This description is useful when asking ChatGPT to:
- Generate new game events or scenarios
- Balance game mechanics (production rates, costs, penalties)
- Create challenge variations
- Design UI improvements
- Write documentation or tutorials
- Suggest strategic tips for players
- Debug game balance issues
- Propose new features or mechanics

---

## Current Development Status

**Implemented Features**:
- ✅ Core resource and building systems
- ✅ Challenge request and approval workflow
- ✅ Food tax automation with scheduler
- ✅ Bank trading with dynamic pricing
- ✅ Team-to-team trading system
- ✅ WebSocket real-time updates
- ✅ Historical scenarios (6 available)
- ✅ Difficulty scaling (Easy/Normal/Hard)
- ✅ OAuth authentication (Online Scout Manager integration)
- ✅ Game timer with pause/resume
- ✅ Event system foundation

**In Development**:
- 🔄 Natural disaster events (earthquake, fire, drought, plague, blizzard, tornado)
- 🔄 Economic events (recession, automation breakthrough)
- 🔄 Event duration tracking and expiration
- 🔄 Advanced mitigation mechanics (infrastructure, hospitals, restaurants)

**Planned Features**:
- 📋 Olympic Games special event
- 📋 Achievement system
- 📋 Post-game statistics dashboard
- 📋 Spectator mode
- 📋 Mobile-responsive design improvements
- 📋 Sound effects and music
- 📋 Tutorial mode for new players
- 📋 Save/load game state

---

## Example ChatGPT Queries

"Using the game description above, suggest 3 new economic events that would create interesting strategic choices."

"Based on The Trading Game mechanics, how should I balance the plague event so it's challenging but not impossible?"

"Design a new building type for The Trading Game that would encourage team cooperation."

"Create 5 new physical challenge types that would fit The Trading Game's gameplay."

"Suggest improvements to the food tax system to make it more engaging."

"Write a beginner's guide for new players explaining the first 15 minutes of gameplay."
