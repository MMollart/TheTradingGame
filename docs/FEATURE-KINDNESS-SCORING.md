# Kindness-Based Trading Score System

## Overview

The Kindness-Based Trading Score system rewards teams that trade generously and discourages exploitative trading behavior. Teams that consistently trade at a loss (helping others) receive a score bonus, while teams that consistently profit from trades receive a penalty.

This feature adds a moral dimension to trading strategy without removing competitive gameplay.

## 📊 How It Works

### Trade Margin Calculation

For each completed team-to-team trade, the system calculates a **trade margin** from each team's perspective:

```
margin = (value_received - value_given) / value_given
```

- **Negative margin**: Trading at a loss (generous/kind) → Score bonus
- **Positive margin**: Trading at a profit (shrewd/exploitative) → Score penalty  
- **Zero margin**: Fair trade → No effect

**Example:**
- Team A gives 10 Food (worth 90 currency based on bank prices)
- Team A receives 50 currency
- Trade margin: (50 - 90) / 90 = **-0.44** (44% loss)

### Reference Prices

Trade margins are calculated using **bank sell prices** as the reference value. This represents the fair market value of resources.

- Bank prices are initialized when the game starts
- Prices may fluctuate based on supply/demand during gameplay
- Currency is always worth its face value

### Aggregate Scoring

At game end, each team's trade history is analyzed:

1. **Weighted Average Margin** is calculated (larger trades have more influence)
2. **Kindness Modifier** is applied to the base score:
   ```
   modifier = 1 - (avg_margin × KINDNESS_FACTOR)
   ```
3. **Final Score** = Base Score × Kindness Modifier

### Configurable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `KINDNESS_FACTOR` | 0.15 | Impact percentage per unit margin (15%) |
| `MIN_KINDNESS_MODIFIER` | 0.5 | Minimum score multiplier (50% cap on penalty) |
| `MAX_KINDNESS_MODIFIER` | 1.5 | Maximum score multiplier (150% cap on bonus) |

## 🏷️ Trading Labels

Teams are assigned labels based on their average trade margin:

| Average Margin | Label | Modifier Effect |
|----------------|-------|-----------------|
| ≤ -20% | **Generous Trader** | +3% or more bonus |
| -20% to -5% | **Fair Trader** | Small bonus |
| -5% to +5% | **Balanced Trader** | Neutral |
| +5% to +20% | **Shrewd Trader** | Small penalty |
| > +20% | **Profit-Focused** | Larger penalty |

## 💾 Database Schema

### New Columns in `trade_offers` Table

| Column | Type | Description |
|--------|------|-------------|
| `from_team_margin` | JSON | Margin data for offering team: `{"margin": -0.15, "trade_value": 100}` |
| `to_team_margin` | JSON | Margin data for receiving team: `{"margin": 0.15, "trade_value": 100}` |

The JSON structure stores:
- `margin`: The calculated trade margin (float)
- `trade_value`: The value of resources given (used for weighting)

### Migration

A database migration (`004_add_trade_margin_columns`) automatically adds these columns when the server starts. The migration is safe to run multiple times.

## 📈 Example Scoring

### Example 1: Generous Team

**Trade History:**
- Trade 1: -25% margin, 100 value
- Trade 2: -30% margin, 150 value  
- Trade 3: -20% margin, 80 value

**Calculation:**
```
Weighted Avg = (-25×100 + -30×150 + -20×80) / 330 = -26.4%
Modifier = 1 - (-0.264 × 0.15) = 1.0396 (approximately 4% bonus)

Base Score: 10,000
Final Score: 10,000 × 1.0396 = 10,396
Label: "Generous Trader"
```

### Example 2: Profit-Focused Team

**Trade History:**
- Trade 1: +30% margin, 100 value
- Trade 2: +25% margin, 150 value

**Calculation:**
```
Weighted Avg = (30×100 + 25×150) / 250 = 27%
Modifier = 1 - (0.27 × 0.15) = 0.9595 (approximately 4% penalty)

Base Score: 10,000
Final Score: 10,000 × 0.9595 = 9,595
Label: "Profit-Focused"
```

## 🔧 Technical Implementation

### Backend Components

**`backend/trade_manager.py`:**
- `TradeMarginCalculator`: Calculates resource values and trade margins
- `TradeManager.accept_trade_offer()`: Records margins when trades complete

**`backend/game_constants.py`:**
- `calculate_kindness_modifier()`: Computes modifier from trade history
- `calculate_final_score()`: Applies kindness modifier to base score

**`backend/main.py`:**
- `end_game()`: Aggregates team trade margins and calculates final scores

**`backend/migrate.py`:**
- Migration `004_add_trade_margin_columns`: Adds database columns

### Testing

**Unit Tests** (`backend/tests/test_kindness_scoring.py`):
- Trade margin calculation
- Kindness modifier calculation
- Score weighting and bounds
- End-to-end scoring scenarios

**Integration Tests** (`backend/tests/test_trading_system.py`):
- Trade margin recording on acceptance
- Database persistence

### Running Tests

```bash
cd backend
pytest tests/test_kindness_scoring.py -v
pytest tests/test_trading_system.py::TestTeamTrading::test_trade_margin_recorded_on_accept -v
```

## 🎮 Gameplay Impact

### Strategic Considerations

**Advantages of Generous Trading:**
- Score boost at game end (up to 50%)
- Builds goodwill with other teams
- Can enable strategic alliances

**Advantages of Profit-Focused Trading:**
- Immediate resource advantage
- Better position during gameplay
- Score penalty capped at 50%

**Balanced Approach:**
- Mix of fair and strategic trades
- Neutral to small modifier effect
- Competitive without penalty

### Player Communication

The system encourages:
- Negotiation and relationship building
- Strategic thinking about long-term vs short-term gains
- Discussion about fairness and cooperation

Post-game, teams see their trading label and can discuss their strategies.

## 🚫 What's NOT Affected

- **Bank trades**: Only team-to-team trades count toward kindness scoring
- **Resource production**: Not affected by trading behavior
- **Building construction**: Costs remain the same
- **Other game mechanics**: Food tax, challenges, disasters are independent

## 🔮 Future Enhancements

Potential additions (not currently implemented):

- **Achievements**: "Most Generous Nation", "Fair Trader Award"
- **Kindness Leaderboard**: Post-game ranking by trade fairness
- **Host Settings**: Adjustable KINDNESS_FACTOR per game
- **Real-time Display**: Show current trade margin during negotiations
- **Historical Trends**: Track kindness across multiple game sessions

## 📝 Configuration

### Adjusting Kindness Impact

To modify the impact of kindness on scoring, edit `backend/game_constants.py`:

```python
# Increase impact (more dramatic bonus/penalty)
KINDNESS_FACTOR = 0.25  # 25% instead of 15%

# Adjust bounds
MIN_KINDNESS_MODIFIER = 0.6  # Less severe penalty cap
MAX_KINDNESS_MODIFIER = 1.4  # Smaller bonus cap
```

**Recommended values:**
- **Educational mode**: `KINDNESS_FACTOR = 0.25` (emphasize cooperation)
- **Competitive mode**: `KINDNESS_FACTOR = 0.10` (less impact, more skill-based)
- **Balanced mode**: `KINDNESS_FACTOR = 0.15` (default)

## 🐛 Troubleshooting

### Margins Not Recording

**Issue**: Trade margins are `null` in database

**Solutions:**
1. Ensure bank prices are initialized: `POST /api/v2/trading/{game_code}/bank/initialize-prices`
2. Check that game was started before trading
3. Verify migration ran successfully (check logs for `004_add_trade_margin_columns`)

### Unexpected Modifier Values

**Issue**: Kindness modifier seems wrong

**Debug steps:**
1. Check `avg_trade_margin` in score output
2. Verify bank prices were set correctly
3. Review completed trades in database: `SELECT * FROM trade_offers WHERE status = 'accepted'`
4. Manually calculate expected margin using reference prices

### Score Calculation Errors

**Issue**: Final score doesn't match expected value

**Check:**
1. Base score components (resources, buildings)
2. Trade margins array in team state
3. Console logs during `end_game()` execution

## 📚 Related Documentation

- [Trading System](TRADING_FEATURE_README.md) - Team-to-team trading mechanics
- [Trading Implementation](TRADING_IMPLEMENTATION_SUMMARY.md) - Technical details
- [Game Flow](FLOW_DIAGRAM.md) - Overall game structure
- [Scoring System](../backend/game_constants.py) - Base scoring calculations

## 🤝 Contributing

When modifying the kindness scoring system:

1. **Run tests** after changes: `pytest tests/test_kindness_scoring.py`
2. **Update constants** if changing formulas
3. **Add tests** for new edge cases
4. **Document** parameter changes in this file
5. **Consider** backward compatibility with existing games

## 📞 Support

For questions or issues with kindness scoring:

1. Check test cases in `test_kindness_scoring.py` for examples
2. Review trade history in database for debugging
3. Verify bank prices are initialized correctly
4. Check server logs for calculation errors
