# Game Events Documentation

This document describes all game events that can occur during The Trading Game, including their targets, impacts, and mitigation strategies.

## Event Severity & Difficulty Scaling

All events use a **severity level** (1-5) and are modified by **game difficulty**:

- **Easy**: 0.75x effect multiplier
- **Normal**: 1.0x effect multiplier  
- **Hard**: 1.5x effect multiplier

Formula: `Final Effect = Base Effect × Severity × Difficulty Modifier`

---

## Natural Disasters

### 🏚️ Earthquake

**Category**: Natural Disaster  
**Targets**: Random buildings across all teams  
**Duration**: Instant (permanent destruction)

**Impact**:
- Destroys **random buildings** from all teams
- Number of buildings destroyed = `(Severity × Difficulty Modifier)` (rounded down)
- **Maximum**: 5 buildings per team (Hard mode, Severity 5)
- Buildings are permanently lost and must be rebuilt

**Scaling Examples**:
| Difficulty | Severity | Buildings Destroyed |
|------------|----------|---------------------|
| Easy       | 3        | 2 (3 × 0.75 = 2.25) |
| Normal     | 3        | 3 (3 × 1.0 = 3)     |
| Hard       | 5        | 5 (5 × 1.5 = 7.5, capped at 5) |

**Mitigation**:
- **Infrastructure buildings**: Each infrastructure building reduces buildings destroyed by 20% (max 100% with 5 infrastructure)
- Protection Formula: `Buildings Destroyed × (1 - Infrastructure Count × 0.2)`

**Implementation Notes**:
- Randomly select building types (including production and optional buildings)
- Cannot destroy buildings that don't exist
- Teams with more buildings are statistically more likely to lose buildings

---

### 🔥 Fire

**Category**: Natural Disaster  
**Targets**: Electrical factories across all teams  
**Duration**: Instant (permanent destruction)

**Impact**:
- Destroys a **percentage of electrical factories** per team (rounded down)
- Base destruction rate: `20%` per team
- Scaled destruction: `Base Rate × Severity × Difficulty Modifier`
- Example: Normal difficulty, Severity 3 = `20% × 3 × 1.0 = 60%` of electrical factories destroyed

**Scaling Examples**:
| Difficulty | Severity | % Destroyed | Team with 5 Factories |
|------------|----------|-------------|------------------------|
| Easy       | 2        | 30%         | 1 factory (1.5)        |
| Normal     | 3        | 60%         | 3 factories (3.0)      |
| Hard       | 4        | 120% (100%) | 5 factories (all)      |

**Mitigation**:
- **Hospitals**: Each hospital reduces destruction by 20% (max 100% with 5 hospitals)
- Protection Formula: `Factories Destroyed × (1 - Hospital Count × 0.2)`
- Teams without electrical factories are unaffected

**Implementation Notes**:
- Only affects electrical factories, not other building types
- Destruction is permanent; factories must be rebuilt
- Medical goods may be required to treat injured workers (optional flavor text)

---

### 💧 Drought

**Category**: Natural Disaster  
**Targets**: Farms and mines across all teams  
**Duration**: 2 food tax cycles

**Impact**:
- **Farms and mines produce 50% less** for duration
- Production modifier: `0.5 × (1 + (Severity - 3) × 0.1)`
- Severity 1-2: Less severe (60% production)
- Severity 3: Standard (50% production)
- Severity 4-5: More severe (40-30% production)

**Scaling Examples**:
| Difficulty | Severity | Production Multiplier | 10 Food/Cycle → |
|------------|----------|-----------------------|-----------------|
| Easy       | 2        | 0.6                   | 6 food          |
| Normal     | 3        | 0.5                   | 5 food          |
| Hard       | 5        | 0.3                   | 3 food          |

**Mitigation**:
- **Infrastructure buildings**: Each infrastructure building reduces impact by 20% (max 100% with 5 infrastructure)
- Protection Formula: `Production Penalty × (1 - Infrastructure Count × 0.2)`
- Example: 50% penalty with 2 infrastructure = `0.5 × (1 - 0.4) = 0.3` penalty → 70% production

**Implementation Notes**:
- Affects both farms AND mines simultaneously
- Duration tracked by food tax cycles, not real-time
- Production returns to normal after 2 tax cycles

---

### 🦠 Plague

**Category**: Natural Disaster (Contagious)  
**Targets**: Individual teams (starts with 1-2 teams)  
**Duration**: Until cured (teams pay medicine to bank)

**Impact**:
- **Decreases all production efficiency** by percentage
- Base production penalty: `30%`
- Scaled penalty: `Base Penalty × Severity × Difficulty Modifier`
- **Spreads between teams during trades** (any resource trade)
- **Infected teams cannot trade with non-infected teams**
- If Olympic Games host has plague: No rewards, all teams get plague after event

**Production Penalty Examples**:
| Difficulty | Severity | Production Penalty | 10 Food/Cycle → |
|------------|----------|--------------------|-----------------| 
| Easy       | 2        | 45%                | 5.5 food        |
| Normal     | 3        | 90%                | 1 food          |
| Hard       | 5        | 225% (100% cap)    | 0 food          |

**Mitigation - Hospitals**:
- **Each hospital reduces production penalty by 20%** (max 100% with 5 hospitals)
- Protection Formula: `Production Penalty × (1 - Hospital Count × 0.2)`
- Example: 90% penalty with 3 hospitals = `0.9 × (1 - 0.6) = 0.36` penalty → 64% production

**Cure Requirements**:
- Teams must deliver **medicine to bank** to cure plague
- Medicine required: `5 × Difficulty Modifier`
  - Easy: 4 medicine (5 × 0.75 = 3.75)
  - Normal: 5 medicine
  - Hard: 8 medicine (5 × 1.5 = 7.5)

**Contagion Rules**:
1. Plague starts with 1-2 random teams (severity-dependent)
2. Any trade between infected and non-infected team spreads plague
3. Infected teams **cannot initiate trades** with non-infected teams
4. Banker can still trade with infected teams (bank is immune)
5. **Olympic Games interaction**: 
   - If host team has plague during event: No rewards distributed
   - All teams become infected after Olympic Games conclude

**Implementation Notes**:
- Track infected teams in game state
- Display infection status prominently in team cards
- Prevent trade modal from opening between infected/non-infected teams
- Medicine payment to bank removes plague from that team only
- Consider visual indicators (red border, skull icon) for infected teams

---

### ❄️ Blizzard

**Category**: Natural Disaster  
**Targets**: All teams (food consumption and production)  
**Duration**: 2 food tax cycles

**Impact**:

**Food Tax Increase**:
- Food tax **doubles** for duration
- Scaled multiplier: `2.0 × Severity × Difficulty Modifier`
- Example: Normal difficulty, Severity 3 = food tax ×6

**Production Decrease**:
- Base production penalty by difficulty:
  - Easy: **-10%** (0.9 production multiplier)
  - Normal: **-20%** (0.8 production multiplier)
  - Hard: **-30%** (0.7 production multiplier)
- Applies to **all production buildings** (farms, mines, factories)

**Scaling Examples**:
| Difficulty | Severity | Food Tax Multiplier | Production Multiplier |
|------------|----------|---------------------|-----------------------|
| Easy       | 2        | ×3 (2 × 2 × 0.75)   | 0.9 (90%)             |
| Normal     | 3        | ×6 (2 × 3 × 1.0)    | 0.8 (80%)             |
| Hard       | 4        | ×12 (2 × 4 × 1.5)   | 0.7 (70%)             |

**Mitigation**:
- **Restaurants**: Generate bonus currency to offset increased food costs
  - Each restaurant provides +20% food tax rebate
  - Example: 100 food tax → 20 currency refund per restaurant
- **Infrastructure**: Reduces production penalty by 10% per building
  - 3 infrastructure buildings: 70% production → 85% production

**Implementation Notes**:
- Duration tracked by food tax cycles (2 cycles)
- Food tax increase applies immediately when tax is triggered
- Production penalty affects ALL buildings, not just farms
- Display blizzard icon/warning in UI during active period

---

### 🌪️ Tornado

**Category**: Natural Disaster  
**Targets**: Resources across all teams  
**Duration**: Instant (permanent resource loss)

**Impact**:
- Removes a **percentage of ALL resources** from each team
- Base resource loss: `15%` of each resource type
- Scaled loss: `Base Loss × Severity × Difficulty Modifier`
- Applied **equally across all resource types** (food, currency, raw materials, electrical goods, medical goods)

**Scaling Examples**:
| Difficulty | Severity | % Resources Lost | Team with 100 of each resource |
|------------|----------|------------------|---------------------------------|
| Easy       | 2        | 22.5%            | Loses 22-23 of each            |
| Normal     | 3        | 45%              | Loses 45 of each               |
| Hard       | 5        | 112.5% (100% cap)| Loses all resources            |

**Mitigation**:
- **Infrastructure buildings**: Each infrastructure building reduces resource loss by 20% (max 100% with 5 infrastructure)
- Protection Formula: `Resources Lost × (1 - Infrastructure Count × 0.2)`
- Example: 45% loss with 2 infrastructure = `0.45 × (1 - 0.4) = 0.27` loss → only 27% lost

**Implementation Notes**:
- Loss applies to ALL resource types simultaneously
- Rounds down (e.g., 22.5 → 22 resources lost)
- Cannot go below 0 resources
- Resources are permanently lost (not recoverable)
- Teams with zero resources are unaffected

---

## Economic Events

### 📉 Economic Recession

**Category**: Economic Event  
**Targets**: Bank prices and building costs (all teams affected)  
**Duration**: 2-4 food tax cycles (scaled by severity)

**Impact**:

**Bank Price Increase**:
- All bank prices **increase by 50%**
- Scaled increase: `50% × Severity × Difficulty Modifier`
- Example: Normal difficulty, Severity 3 = +150% price increase (×2.5 multiplier)

**Building Cost Increase**:
- All building costs **increase by 25%**
- Scaled increase: `25% × Severity × Difficulty Modifier`
- Example: Hard difficulty, Severity 4 = +150% cost increase (×2.5 multiplier)

**Duration**:
- Base duration: 2 food tax cycles
- Duration: `2 + (Severity - 3)` tax cycles
  - Severity 1: 0 cycles (event doesn't occur)
  - Severity 2: 1 cycle
  - Severity 3: 2 cycles
  - Severity 4: 3 cycles
  - Severity 5: 4 cycles

**Scaling Examples**:
| Difficulty | Severity | Bank Price Mult. | Build Cost Mult. | Duration |
|------------|----------|------------------|------------------|----------|
| Easy       | 2        | ×1.75 (75% up)   | ×1.375 (37.5% up)| 1 cycle  |
| Normal     | 3        | ×2.5 (150% up)   | ×1.75 (75% up)   | 2 cycles |
| Hard       | 5        | ×4.75 (375% up)  | ×2.875 (187% up) | 4 cycles |

**Mitigation**:
- **Infrastructure buildings**: Each infrastructure building reduces impact by 20% (max 100% with 5 infrastructure)
- Price increase reduction: `Price Multiplier × (1 - Infrastructure Count × 0.2)`
- Example: ×2.5 multiplier with 3 infrastructure = `2.5 × (1 - 0.6) = 1.0` → no price increase!

**Rewards**:
- **Restaurants**: Each restaurant generates **bonus currency** during recession
  - Bonus: `50 currency × Severity × Difficulty Modifier` per cycle per restaurant
  - Represents "economic stimulus" or "comfort food demand"
  - Example: 3 restaurants, Normal difficulty, Severity 3 = +450 currency per cycle

**Implementation Notes**:
- Duration tracked by food tax cycles
- Price/cost increases apply immediately when event triggers
- Existing builds in progress use old costs (or apply new costs immediately - design choice)
- Display "recession active" warning in bank and build UI
- Restaurant bonuses delivered at each food tax cycle during recession

---

## Positive Events

### 🤖 Automation Breakthrough

**Category**: Positive Economic Event  
**Targets**: One random team (or team with most factories)  
**Duration**: 2 food tax cycles

**Impact**:
- **All factories produce +50%** for duration
- Scaled bonus: `50% × Severity × Difficulty Modifier`
- Applies to: Electrical factories and medical factories
- **Requires 30 electrical goods upfront** to implement automation
- Teams without enough electrical goods **miss the entire bonus**

**Scaling Examples**:
| Difficulty | Severity | Production Bonus | 10 Goods/Cycle → | E. Goods Required |
|------------|----------|------------------|------------------|-------------------|
| Easy       | 2        | +75%             | 17.5 goods       | 22 (30 × 0.75)    |
| Normal     | 3        | +150%            | 25 goods         | 30                |
| Hard       | 5        | +375%            | 47.5 goods       | 45 (30 × 1.5)     |

**Electrical Goods Requirement**:
- Base cost: `30 electrical goods`
- Scaled cost: `30 × Difficulty Modifier`
  - Easy: 22 electrical goods (30 × 0.75 = 22.5)
  - Normal: 30 electrical goods
  - Hard: 45 electrical goods (30 × 1.5)

**Selection Logic**:
- **Option 1**: Random team (pure RNG)
- **Option 2**: Team with most factories (rewards production focus)
- **Option 3**: Weighted random (teams with more factories have higher chance)

**Implementation Notes**:
- Selected team receives notification: "Automation Breakthrough Available!"
- Team has **one food tax cycle to pay** electrical goods to bank
- If paid: Production bonus applies for next 2 tax cycles
- If not paid: Bonus is forfeited, event ends
- Production bonus applies only to electrical factories and medical factories
- Does NOT affect farms, mines, or service buildings

**Banker Interaction**:
- Banker can strategically choose which team receives breakthrough
- Can be used to balance game if one team is falling behind
- Creates interesting trade dynamics (other teams may offer to help pay electrical goods)

---

## Event Trigger Rules

### Event Frequency
- Events can be triggered manually by banker/host
- Events should not stack (only one major event active at a time)
- Recommended cooldown: 3-5 food tax cycles between major events

### Severity Guidelines
- **Severity 1-2**: Minor impact, tutorial/easy mode
- **Severity 3**: Standard impact, recommended for balanced games
- **Severity 4-5**: Major impact, challenging/dramatic moments

### Event Selection Strategy
- **Early game**: Use low-severity events (1-2) to introduce mechanics
- **Mid game**: Moderate severity (3) to create strategic decisions
- **Late game**: High severity (4-5) for dramatic finishes

### Combining Events
- Avoid combining multiple negative events simultaneously
- Consider "recovery events" (Automation Breakthrough) after major disasters
- Plague + Blizzard = potential softlock (avoid this combination)

---

## Implementation Checklist

### Per-Event Implementation
- [ ] Backend logic in `main.py` (event handler function)
- [ ] Database schema for tracking event state (if needed)
- [ ] WebSocket broadcast to all teams
- [ ] Frontend UI display (notification + status card)
- [ ] Team state updates (resources, production modifiers)
- [ ] Duration tracking (tax cycle counter)
- [ ] Mitigation calculations (infrastructure, hospitals, restaurants)
- [ ] Event log entries with details
- [ ] Visual indicators during active events
- [ ] Sound effects (optional)

### Testing Requirements
- Test at all difficulty levels (Easy, Normal, Hard)
- Test at all severity levels (1-5)
- Test mitigation buildings (0, 1, 3, 5 buildings)
- Test edge cases (zero resources, zero buildings)
- Test event expiration (duration tracking)
- Test multiple teams simultaneously
- Test event stacking/overlap prevention

---

## Future Event Ideas

### Natural Disasters
- **Heatwave**: Increased food spoilage, electrical goods demand spikes
- **Tsunami**: Coastal nations only, destroys infrastructure buildings
- **Volcanic Eruption**: Ash cloud halts production for 1 cycle, but fertile soil increases farm output afterward
- **Meteor Strike**: Single team loses significant resources, but gains rare materials

### Economic Events
- **Tech Boom**: Electrical goods prices increase 200%, electrical factories gain production bonus
- **Medical Crisis**: Medical goods prices skyrocket, hospitals become critical
- **Trade War**: Bank prices increase for one team, decrease for another
- **Currency Devaluation**: One team's currency worth 50% less for 2 cycles

### Social Events
- **Olympic Games**: Host team spends resources but earns prestige/rewards
- **World's Fair**: Teams can invest resources to gain permanent production bonuses
- **Summit Meeting**: Teams can cooperate to unlock special technologies
- **Revolution**: Random team's resources redistributed to other teams

### Positive Events
- **Bumper Harvest**: All farms produce +50% for 1 cycle
- **Resource Discovery**: Random team gains bonus raw materials
- **Scientific Breakthrough**: One building type becomes cheaper for all teams
- **Diplomatic Success**: Free trade (no bank fees) for 2 cycles

---

## Configuration File Structure

For implementation, consider this JSON structure for event definitions:

```json
{
  "earthquake": {
    "category": "natural_disaster",
    "base_effect": 1.0,
    "max_effect": 5,
    "duration_cycles": 0,
    "targets": "buildings",
    "mitigation": {
      "infrastructure": 0.2
    },
    "difficulty_scaling": true
  },
  "plague": {
    "category": "natural_disaster",
    "base_effect": 0.3,
    "duration_cycles": -1,
    "cure_cost": 5,
    "targets": "production",
    "contagious": true,
    "mitigation": {
      "hospital": 0.2
    },
    "difficulty_scaling": true
  }
}
```

This allows dynamic event loading and easier balancing adjustments without code changes.
