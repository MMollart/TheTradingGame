# Enhanced Scoring System Proposal

**Status**: 📋 Proposal  
**Related Issues**: #94 (Trade Fairness Modifier)  
**Date**: November 7, 2025

## Overview

This proposal outlines an enhanced scoring system that rewards multiple strategic dimensions beyond just resource accumulation and building construction. The goal is to create a richer, more strategic endgame that encourages diverse playstyles and rewards cooperation, efficiency, and long-term planning.

## Current Scoring System

Currently, final scores are calculated based on:
- **Resource Value**: Total resources × current bank prices
- **Building Value**: Total buildings × their currency cost (doubled)
- **Trade Value**: Manual trade tracking (not automated)
- **Kindness Value**: Manual kindness tracking (not automated)

**Location**: `backend/game_constants.py` - `calculate_final_score()`

**Limitations**:
- Heavily weighted toward final resource/building count
- No reward for strategic choices (efficiency, diversity, planning)
- No penalty for poor resource management (debt, food failures)
- Trade fairness not tracked or scored (Issue #94)
- Challenge completion not factored into score
- Social/cooperative play not incentivized

---

## Proposed Enhanced Components

### 1. 🤝 **Trade Fairness Modifier** (Issue #94 - Priority 1)

**Concept**: Reward teams that trade generously, penalize those who exploit others.

**Implementation**:
```python
"trade_fairness_modifier": 1.0,  # Multiplicative modifier (0.5 to 1.5)

# During trade completion:
bank_price = get_bank_price(resource_type)
fair_value = bank_price * quantity
actual_value = trade_price
margin = (actual_value - fair_value) / fair_value

# Track per team:
team.trade_margins.append(margin)
team.avg_trade_margin = weighted_average(team.trade_margins)

# At score calculation:
kindness_factor = 0.15  # Tunable parameter
trade_fairness_modifier = 1 + (avg_trade_margin * kindness_factor)
trade_fairness_modifier = max(0.5, min(1.5, trade_fairness_modifier))  # Cap at ±50%

# Apply to final score:
final_score *= trade_fairness_modifier
```

**Database Changes**:
```sql
ALTER TABLE trades ADD COLUMN margin FLOAT;
ALTER TABLE players ADD COLUMN avg_trade_margin FLOAT DEFAULT 0;
ALTER TABLE players ADD COLUMN trade_fairness_modifier FLOAT DEFAULT 1.0;
```

**Display**:
- "Generous Trader" (+20% bonus)
- "Fair Trader" (±5%)
- "Shrewd Trader" (-15% penalty)

---

### 2. 🏆 **Challenge Completion Bonus** (Priority 2)

**Concept**: Reward teams for completing physical challenges (encourages activity).

**Implementation**:
```python
"challenge_completion_value": 0,  # Additive bonus

challenges_completed = nation_state.get("challenges_completed", 0)
score["challenge_completion_value"] = challenges_completed * 50  # 50 pts per challenge
```

**Tracking**:
- Increment counter in `player_state` on each successful challenge
- Aggregate at team level for scoring

**Typical Values**:
- 10 challenges = 500 points
- 20 challenges = 1000 points
- 30 challenges = 1500 points

---

### 3. 🍔 **Food Security Score** (Priority 3)

**Concept**: Reward teams that consistently paid food tax without failure.

**Implementation**:
```python
"food_security_bonus": 0,  # Additive bonus

food_tax_failures = nation_state.get("food_tax_failures", 0)
food_tax_successes = nation_state.get("food_tax_successes", 0)

if food_tax_successes > 0:
    success_rate = (food_tax_successes - food_tax_failures) / food_tax_successes
    score["food_security_bonus"] = success_rate * 300  # Up to 300 pts for 100% success
```

**Tracking**:
- Track in `game_state.teams[team_id].food_tax_stats`
- Increment `successes` on successful payment
- Increment `failures` on failed payment

**Typical Values**:
- 100% success = 300 points
- 80% success = 240 points
- 50% success = 150 points

---

### 4. 🌱 **Diversity Bonus** (Priority 4)

**Concept**: Reward teams that diversify their economy (multiple resource types and building types).

**Implementation**:
```python
"diversity_bonus": 0,  # Additive bonus

# Resource diversity
resources = nation_state.get("resources", {})
resource_types_with_stock = sum(1 for amount in resources.values() if amount > 10)
resource_diversity_score = resource_types_with_stock * 100  # 100 pts per resource type

# Building diversity
buildings = nation_state.get("buildings", {})
building_types_built = sum(1 for count in buildings.values() if count > 0)
building_diversity_score = building_types_built * 75  # 75 pts per building type

score["diversity_bonus"] = resource_diversity_score + building_diversity_score
```

**Typical Values**:
- 5 resources + 8 buildings = 1100 points
- 3 resources + 5 buildings = 675 points
- 2 resources + 3 buildings = 425 points

**Strategic Impact**: Encourages teams to build balanced economies rather than specializing in one resource.

---

### 5. 🏥 **Social Investment Multiplier** (Priority 5)

**Concept**: Schools, hospitals, and restaurants multiply your score (society-building).

**Implementation**:
```python
"social_multiplier": 1.0,  # Multiplicative modifier

social_buildings = (
    nation_state.get("buildings", {}).get("hospital", 0) +
    nation_state.get("buildings", {}).get("school", 0) +
    nation_state.get("buildings", {}).get("restaurant", 0)
)
social_multiplier = 1.0 + (social_buildings * 0.02)  # +2% per social building

# Apply at end:
score["total"] *= social_multiplier
```

**Typical Values**:
- 5 social buildings = 1.10× multiplier (+10%)
- 10 social buildings = 1.20× multiplier (+20%)
- 15 social buildings = 1.30× multiplier (+30%)

**Strategic Impact**: Makes service buildings valuable beyond their immediate utility.

---

## Additional Components (Lower Priority)

### 6. ⚡ **Efficiency Score**

**Concept**: Reward teams with high production-to-consumption ratios.

```python
"efficiency_bonus": 0,

production_buildings = sum([
    buildings.get("farm", 0),
    buildings.get("mine", 0),
    buildings.get("electrical_factory", 0),
    buildings.get("medical_factory", 0)
])

service_buildings = sum([
    buildings.get("school", 0),
    buildings.get("hospital", 0),
    buildings.get("restaurant", 0),
    buildings.get("infrastructure", 0)
])

if service_buildings > 0:
    efficiency_ratio = production_buildings / service_buildings
    score["efficiency_bonus"] = efficiency_ratio * 200
```

---

### 7. 💰 **Wealth Growth Rate**

**Concept**: Reward teams that grew their wealth (not just final value).

```python
"growth_rate_bonus": 0,

starting_value = nation_state.get("starting_total_value", 1000)  # Tracked at game start
current_value = score["resource_value"] + score["building_value"]
growth_rate = (current_value - starting_value) / starting_value
score["growth_rate_bonus"] = growth_rate * 500  # Up to 500 pts for 100% growth
```

**Tracking Required**: Save `starting_total_value` when game starts.

---

### 8. 🌍 **Infrastructure Resilience Bonus**

**Concept**: Reward teams that invested in infrastructure (prepared for disasters).

```python
"resilience_bonus": 0,

infrastructure_count = nation_state.get("buildings", {}).get("infrastructure", 0)
disasters_survived = nation_state.get("disasters_survived", 0)
score["resilience_bonus"] = (infrastructure_count * 100) + (disasters_survived * 50)
```

**Tracking Required**: Increment `disasters_survived` when disaster events occur.

---

### 9. 🤝 **Trade Activity Bonus**

**Concept**: Reward active traders (encourages market participation).

```python
"trade_activity_bonus": 0,

total_trades = nation_state.get("total_trades", 0)
score["trade_activity_bonus"] = min(total_trades * 25, 500)  # Cap at 20 trades
```

---

### 10. 🎖️ **Challenge Streak Multiplier**

**Concept**: Consecutive challenge successes increase rewards exponentially.

```python
"challenge_streak_bonus": 0,

max_streak = nation_state.get("max_challenge_streak", 0)
score["challenge_streak_bonus"] = (max_streak ** 1.5) * 20  # Exponential reward
```

**Tracking Required**: Track current streak and max streak per team.

---

### 11. 💎 **Resource Rarity Bonus**

**Concept**: Advanced resources (electrical goods, medical goods) worth more than basics.

```python
"rarity_bonus": 0,

electrical_goods = resources.get("electrical_goods", 0)
medical_goods = resources.get("medical_goods", 0)
score["rarity_bonus"] = (electrical_goods * 2) + (medical_goods * 3)
```

---

### 12. 🧘 **Sustainability Score**

**Concept**: Penalize teams with negative currency (debt), reward positive balance.

```python
"sustainability_score": 0,

currency = resources.get("currency", 0)
if currency < 0:
    score["sustainability_score"] = currency * 0.5  # Penalty for debt
else:
    score["sustainability_score"] = min(currency * 0.1, 200)  # Bonus, capped at 200
```

---

### 13. 🏛️ **Scenario-Specific Bonuses**

**Concept**: Different historical scenarios reward different behaviors.

```python
"scenario_bonus": 0,

scenario = nation_state.get("scenario_id", "")

if scenario == "space_race":
    # Reward tech buildings
    tech_score = (
        buildings.get("electrical_factory", 0) * 200 +
        buildings.get("school", 0) * 150
    )
    score["scenario_bonus"] += tech_score

elif scenario == "industrial_revolution":
    # Reward production buildings
    production_score = (
        buildings.get("farm", 0) * 100 +
        buildings.get("mine", 0) * 100
    )
    score["scenario_bonus"] += production_score

elif scenario == "renaissance":
    # Reward social buildings
    social_score = (
        buildings.get("hospital", 0) * 150 +
        buildings.get("restaurant", 0) * 150
    )
    score["scenario_bonus"] += social_score
```

---

### 14. ⏱️ **Time Efficiency Bonus**

**Concept**: Reward teams that achieved high scores quickly.

```python
"time_efficiency_bonus": 0,

game_duration_minutes = nation_state.get("game_duration_minutes", 120)
time_remaining_minutes = nation_state.get("time_remaining_minutes", 0)

if time_remaining_minutes > 0:
    time_bonus_ratio = time_remaining_minutes / game_duration_minutes
    score["time_efficiency_bonus"] = time_bonus_ratio * 400
```

---

## Proposed Final Score Structure

```python
def calculate_final_score(nation_state: Dict) -> Dict:
    """
    Enhanced scoring system with multiple strategic dimensions.
    """
    score = {
        # === BASE COMPONENTS (Additive) ===
        "resource_value": 0,
        "building_value": 0,
        
        # === STRATEGIC BONUSES (Additive) ===
        "challenge_completion_value": 0,
        "food_security_bonus": 0,
        "diversity_bonus": 0,
        "efficiency_bonus": 0,
        "resilience_bonus": 0,
        "trade_activity_bonus": 0,
        "challenge_streak_bonus": 0,
        "rarity_bonus": 0,
        "sustainability_score": 0,
        "growth_rate_bonus": 0,
        "scenario_bonus": 0,
        "time_efficiency_bonus": 0,
        
        # === MULTIPLIERS (Multiplicative) ===
        "trade_fairness_modifier": 1.0,  # 0.5 to 1.5
        "social_multiplier": 1.0,         # 1.0 to 1.3
        
        # === TOTALS ===
        "base_total": 0,      # Sum of additive components
        "total": 0            # After multipliers
    }
    
    # Calculate base components
    # ... (resource_value, building_value calculations)
    
    # Calculate strategic bonuses
    # ... (each component as detailed above)
    
    # Sum additive components
    score["base_total"] = sum([
        score["resource_value"],
        score["building_value"],
        score["challenge_completion_value"],
        score["food_security_bonus"],
        score["diversity_bonus"],
        score["efficiency_bonus"],
        score["resilience_bonus"],
        score["trade_activity_bonus"],
        score["challenge_streak_bonus"],
        score["rarity_bonus"],
        score["sustainability_score"],
        score["growth_rate_bonus"],
        score["scenario_bonus"],
        score["time_efficiency_bonus"]
    ])
    
    # Apply multipliers
    score["total"] = (
        score["base_total"] * 
        score["trade_fairness_modifier"] * 
        score["social_multiplier"]
    )
    
    return score
```

---

## Implementation Priority Tiers

### **Tier 1: Essential (High Impact, Low Effort)**
1. ✅ Trade Fairness Modifier (Issue #94)
2. ✅ Challenge Completion Bonus
3. ✅ Food Security Score
4. ✅ Diversity Bonus
5. ✅ Social Investment Multiplier

**Why**: These five create immediate strategic depth with minimal tracking overhead. They reward distinct playstyles (cooperation, activity, planning, diversity, society-building).

---

### **Tier 2: Valuable (Medium Impact, Medium Effort)**
6. Efficiency Score
7. Trade Activity Bonus
8. Resilience Bonus
9. Sustainability Score

**Why**: Add nuance to scoring but require moderate tracking.

---

### **Tier 3: Advanced (High Impact, High Effort)**
10. Wealth Growth Rate (requires start-of-game tracking)
11. Challenge Streak Multiplier (requires streak tracking)
12. Scenario-Specific Bonuses (requires scenario-aware logic)
13. Time Efficiency Bonus (requires time tracking)

**Why**: Require additional data tracking throughout the game.

---

### **Tier 4: Polish (Low Impact, Optional)**
14. Resource Rarity Bonus (marginal impact)

---

## Database Schema Changes

### Required for Tier 1:

```sql
-- Trade fairness tracking
ALTER TABLE trades ADD COLUMN margin FLOAT DEFAULT 0;

-- Player/team stats
ALTER TABLE players ADD COLUMN challenges_completed INT DEFAULT 0;
ALTER TABLE players ADD COLUMN food_tax_successes INT DEFAULT 0;
ALTER TABLE players ADD COLUMN food_tax_failures INT DEFAULT 0;
ALTER TABLE players ADD COLUMN total_trades INT DEFAULT 0;
ALTER TABLE players ADD COLUMN avg_trade_margin FLOAT DEFAULT 0;

-- Score components (for display)
ALTER TABLE game_sessions ADD COLUMN final_scores JSON;
```

### Optional for Tier 2+:

```sql
ALTER TABLE players ADD COLUMN disasters_survived INT DEFAULT 0;
ALTER TABLE players ADD COLUMN max_challenge_streak INT DEFAULT 0;
ALTER TABLE players ADD COLUMN current_challenge_streak INT DEFAULT 0;
ALTER TABLE players ADD COLUMN starting_total_value INT DEFAULT 0;
```

---

## Configuration & Tuning

Create a configuration system for score weights:

```python
SCORING_CONFIG = {
    "weights": {
        "challenge_completion": 50,      # Points per challenge
        "food_security": 300,             # Max bonus for 100% success
        "resource_diversity": 100,        # Points per resource type
        "building_diversity": 75,         # Points per building type
        "social_building": 0.02,          # Multiplier per social building
        "trade_fairness_factor": 0.15,    # Scaling factor for margin
        "trade_activity": 25,             # Points per trade
        "resilience_infrastructure": 100, # Points per infrastructure
        "resilience_disaster": 50,        # Points per disaster survived
    },
    "caps": {
        "trade_fairness_min": 0.5,   # Minimum multiplier
        "trade_fairness_max": 1.5,   # Maximum multiplier
        "social_multiplier_max": 1.3, # Maximum social multiplier
        "trade_activity_max": 500,    # Maximum trade activity bonus
        "sustainability_max": 200,    # Maximum sustainability bonus
    }
}
```

This allows hosts to tune scoring emphasis based on educational goals or competitive balance.

---

## Display & Transparency

### Post-Game Score Breakdown (UI Enhancement):

```
🏆 Team Phoenix Final Score: 4,850 points

Base Components:
  💰 Resource Value:        2,000 pts
  🏗️  Building Value:        1,500 pts
  
Strategic Bonuses:
  🏆 Challenge Completion:    600 pts (12 challenges)
  🍔 Food Security:           270 pts (90% success rate)
  🌱 Diversity:               675 pts (3 resources, 6 buildings)
  🏥 Social Investment:      ×1.10 (5 social buildings)
  
Trade Performance:
  🤝 Trade Fairness:         ×1.08 (+8% generous trader)
  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Base Total:                4,045 pts
× Social Multiplier:       ×1.10
× Trade Fairness:          ×1.08
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL SCORE:              4,850 pts
```

---

## Balancing Considerations

### Typical Score Ranges (estimated):

**Base Components**: 2,000-5,000 pts
- Resources: 1,000-3,000 pts
- Buildings: 1,000-2,000 pts

**Strategic Bonuses**: 500-2,000 pts
- Challenges: 200-800 pts (4-16 challenges)
- Food Security: 0-300 pts
- Diversity: 300-1,100 pts
- Others: 0-500 pts

**Multipliers**: ×0.8 to ×1.5
- Trade Fairness: ×0.5 to ×1.5
- Social Investment: ×1.0 to ×1.3
- Combined: ×0.5 to ×1.95

**Total Score Range**: 1,500-12,000 pts

**Relative Weights**:
- Base wealth: ~50-60% of score
- Strategic bonuses: ~20-30% of score
- Multiplier effects: ~10-20% impact

---

## Testing Plan

### Phase 1: Individual Component Testing
- Test each scoring component in isolation
- Verify calculations with known inputs
- Check edge cases (zero values, negative values, caps)

### Phase 2: Integration Testing
- Test combined scoring with realistic game states
- Verify multipliers apply correctly
- Check total score consistency

### Phase 3: Balance Testing
- Run simulations with different playstyles
- Ensure no single strategy dominates
- Adjust weights/caps as needed

### Phase 4: User Testing
- Run live games with new scoring
- Gather feedback on strategic impact
- Monitor for unintended exploits

---

## Migration Path

### Step 1: Database Schema (v1.1.0)
- Add new columns to `players` and `trades` tables
- Migrate existing games (set defaults)

### Step 2: Tracking Implementation (v1.2.0)
- Add counters for challenges, food tax, trades
- Track trade margins during trade completion
- Store starting values at game start

### Step 3: Scoring Logic (v1.3.0)
- Implement Tier 1 components only
- Update `calculate_final_score()`
- Add score breakdown to game end response

### Step 4: UI Updates (v1.4.0)
- Display score breakdown in post-game report
- Add real-time fairness indicators
- Show strategic progress during game

### Step 5: Advanced Features (v2.0.0)
- Implement Tier 2-3 components
- Add configuration system
- Host settings for score tuning

---

## Future Enhancements

### Achievement System
Tie scoring components to achievements:
- "Generous Saint" - Maintain +20% trade fairness
- "Workout Warrior" - Complete 20+ challenges
- "Food Champion" - 100% food tax success
- "Renaissance Team" - Max diversity bonus
- "Social Builders" - 10+ social buildings

### Leaderboard Categories
Multiple leaderboard rankings:
- Overall Score
- Trade Fairness Champion
- Challenge Champion
- Most Diversified
- Best Growth Rate

### Progressive Difficulty
Scale bonus values by difficulty:
- Easy: 1.5× bonus multipliers (generous)
- Normal: 1.0× bonus multipliers (standard)
- Hard: 0.75× bonus multipliers (challenging)

---

## Open Questions

1. **Should trade fairness be symmetric?**
   - If Team A profits, should Team B's penalty exactly offset?
   - Or should both teams be evaluated independently?

2. **How to handle bank trades?**
   - Include in fairness calculation? (probably not)
   - Track separately? (recommended)

3. **Should multipliers stack multiplicatively?**
   - Currently: `base × trade_fairness × social_multiplier`
   - Alternative: `base × (1 + sum_of_modifier_deltas)`

4. **Cap total multiplier?**
   - Maximum combined multiplier: 2.0×?
   - Prevents extreme runaway scores

5. **Display during game or only at end?**
   - Real-time feedback more engaging
   - But could distract from gameplay

---

## References

- **Issue #94**: Trade Fairness Modifier proposal
- **File**: `backend/game_constants.py` - Current scoring logic
- **File**: `backend/game_logic.py` - Score calculation integration
- **Doc**: `docs/game-design/GAME_EVENTS.md` - Event system integration
- **Doc**: `docs/technical/TRADING_FEATURE_README.md` - Trading system

---

## Approval & Next Steps

**Recommended Action**:
1. Review and approve Tier 1 components
2. Create GitHub issues for each component
3. Implement database schema changes
4. Build Tier 1 scoring components
5. Test and balance
6. Deploy as opt-in feature (toggle in game settings)
7. Gather player feedback
8. Iterate based on data

**Timeline Estimate**:
- Tier 1 implementation: 2-3 weeks
- Testing & balancing: 1-2 weeks
- Tier 2 implementation: 2-3 weeks
- Full deployment: 6-8 weeks total
