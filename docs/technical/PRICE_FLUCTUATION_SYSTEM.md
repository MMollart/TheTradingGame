# Dynamic Bank Price Fluctuation System

## Overview

The price fluctuation system adds realistic market dynamics to bank resource prices through random variations influenced by momentum, mean reversion, and active game events.

## Key Features

### 1. Random Fluctuations
- **Frequency**: Every second, each resource has a 3.33% chance of price change
- **Magnitude**: ±2% variation per change
- **Bounds**: Prices constrained to 0.5x - 2.0x baseline
- **Spread**: Buy price always exceeds sell price by ~10%

### 2. Momentum System
- **Lookback Period**: Last 2 minutes of price history
- **Weight**: 60% influence on next change direction
- **Behavior**: Rising prices tend to continue rising; falling prices tend to continue falling
- **Implementation**: Analyzes average percentage change over recent history

### 3. Mean Reversion
- **Target**: Return to baseline over approximately 15 minutes
- **Weight**: 40% influence on next change direction
- **Pressure**: Increases proportionally with distance from baseline
- **Balance**: Gentle pull that doesn't override strong momentum

### 4. Game Event Effects

Events modify price change probabilities through `price_effect` values:

| Event | Effect | Resources | Description |
|-------|--------|-----------|-------------|
| Economic Recession | +0.3 | All | Prices more likely to increase |
| Automation Breakthrough | -0.2 | All | Prices more likely to decrease |
| Drought | +0.2 | Food, Raw Materials | Scarcity drives prices up |
| Plague | +0.25 | Medical Goods | High demand for medicine |
| Fire | +0.15 | Electrical Goods | Factory destruction reduces supply |
| Blizzard | +0.15 | Food | Cold weather affects food supply |
| Earthquake | +0.1 | All | General economic disruption |
| Tornado | +0.1 | All | Resource destruction |

## Technical Architecture

### Components

**1. PricingManager (`pricing_manager.py`)**
- Core logic for price calculations
- Momentum and mean reversion algorithms
- Event effect integration
- Price constraint enforcement

**2. Price Fluctuation Scheduler (`price_fluctuation_scheduler.py`)**
- Background task running every 1 second
- Processes all active games
- Broadcasts price updates via WebSocket
- Records changes in PriceHistory table

**3. Event Configuration (`event_config.json`)**
- Defines price_effect for each event type
- Optionally specifies price_effect_resources for targeted effects
- Loaded dynamically by PricingManager

### Key Methods

#### `apply_random_fluctuation(game_code, current_prices)`
Main fluctuation logic:
1. Check 3.33% probability for each resource
2. Calculate momentum bias from recent history
3. Calculate mean reversion pressure
4. Get active event effects
5. Combine factors: `(60% × momentum) + (40% × reversion) + event_effect`
6. Apply biased random change
7. Enforce bounds and spread constraints
8. Record in price history

#### `_calculate_momentum_bias(game_session_id, resource_type)`
Analyzes recent price changes:
- Queries PriceHistory for last 2 minutes
- Calculates average percentage change
- Normalizes to -1 to +1 range (±5% = max momentum)
- Returns positive for upward trend, negative for downward

#### `_calculate_mean_reversion_pressure(current_price, baseline)`
Calculates pull towards baseline:
- Measures deviation from baseline as percentage
- Inverts sign (high price → negative pressure)
- Scales by MAX/MIN multiplier range
- Returns -1 to +1 (towards baseline)

#### `_get_active_event_effect(game, event_effects)`
Combines effects from active events:
- Reads game.game_state['active_events']
- Looks up price_effect for each event
- Handles resource-specific effects
- Returns dict of cumulative effects per resource

## Data Flow

```
1. Scheduler triggers every 1 second
   ↓
2. For each active game:
   - Load current bank_prices from game_state
   ↓
3. PricingManager.apply_random_fluctuation()
   - For each resource (3.33% chance):
     a. Calculate momentum from PriceHistory
     b. Calculate mean reversion pressure
     c. Get event effects from active_events
     d. Combine: (0.6 × momentum) + (0.4 × reversion) + events
     e. Apply biased random ±2% change
     f. Enforce bounds and spread
   ↓
4. If prices changed:
   - Update game.game_state['bank_prices']
   - Record in PriceHistory table
   - Broadcast WebSocket event to all players
```

## WebSocket Events

### `bank_prices_updated`
Broadcast when prices change:
```json
{
  "type": "event",
  "event_type": "bank_prices_updated",
  "data": {
    "prices": {
      "food": {
        "baseline": 2,
        "buy_price": 2,
        "sell_price": 1
      },
      "raw_materials": { ... },
      ...
    },
    "changed_resources": ["food", "raw_materials"],
    "timestamp": "2025-11-07T10:30:45.123Z"
  }
}
```

## Configuration Constants

Located in `PricingManager` class:

```python
# Bounds
MIN_MULTIPLIER = 0.5       # -50% from baseline
MAX_MULTIPLIER = 2.0       # +100% from baseline
SPREAD_PERCENTAGE = 0.1    # 10% buy/sell spread

# Fluctuation
FLUCTUATION_PROBABILITY = 0.0333  # 3.33% per second
FLUCTUATION_MAGNITUDE = 0.02      # ±2% change

# Momentum
MOMENTUM_LOOKBACK_MINUTES = 2     # 2 minutes history
MOMENTUM_WEIGHT = 0.6             # 60% weight

# Mean Reversion
MEAN_REVERSION_TARGET_MINUTES = 15  # ~15 min to baseline
```

## Database Schema

### PriceHistory Table
Records every price change:
- `game_session_id`: Foreign key to game
- `resource_type`: Resource name (string)
- `buy_price`: Bank's sell price to teams
- `sell_price`: Bank's buy price from teams
- `baseline_price`: Original fixed price
- `timestamp`: When change occurred
- `triggered_by_trade`: False for fluctuations, True for trade-based

## Testing

Comprehensive test suite in `tests/test_price_fluctuation.py`:

### Test Categories
1. **Momentum Calculations**
   - Upward/downward/flat trends
   - Proper normalization to -1 to +1

2. **Mean Reversion**
   - Above/below/at baseline
   - Proportional pressure scaling

3. **Price Constraints**
   - Buy > sell spread maintained
   - MIN/MAX bounds enforced
   - Rounding doesn't break constraints

4. **Event Effects**
   - Positive/negative effects
   - Resource-specific targeting
   - Multiple simultaneous events

5. **Probability Mechanics**
   - 3.33% frequency validated statistically
   - ±2% magnitude respected
   - Proper randomization

6. **Price History**
   - All changes recorded
   - Marked as non-trade triggered
   - Queryable for momentum calculations

## Usage Example

### Starting the System
Scheduler starts automatically with the application:
```python
# In main.py on_startup()
start_price_fluctuation_scheduler()
```

### Accessing Current Prices
```python
# Prices stored in game_state
current_prices = game.game_state['bank_prices']

# Example structure:
{
  "food": {
    "baseline": 2,
    "buy_price": 2,    # Bank sells to teams at this price
    "sell_price": 1    # Bank buys from teams at this price
  },
  "raw_materials": { ... }
}
```

### Querying Price History
```python
pricing_mgr = PricingManager(db)
history = pricing_mgr.get_price_history(
    game_code="ABC123",
    resource_type="food",  # Optional filter
    limit=100              # Recent 100 records
)
```

## Performance Considerations

### Optimization Strategies
1. **Probability Check First**: 96.67% of resources skip processing each second
2. **Batch Processing**: All resources checked in single scheduler pass
3. **Minimal Database Queries**: Only when changes occur
4. **Indexed PriceHistory**: Timestamp and game_session_id indexed

### Load Estimate
- Active games: 10
- Resources per game: 4
- Checks per second: 40
- Actual changes per second: ~1.3 (3.33% of 40)
- Database writes per second: ~1.3
- WebSocket broadcasts per second: ~0.3 (multiple resources can change together)

**Result**: Minimal server load, even with many active games.

## Future Enhancements

### Potential Additions
1. **Volatility Settings**: Game config for high/medium/low volatility
2. **Market Depth**: Larger trades have bigger price impact
3. **Predictive Indicators**: UI hints about trend direction
4. **Price Alerts**: Notify players of significant changes
5. **Historical Charts**: Visual price trends over game duration
6. **Circuit Breakers**: Pause fluctuations during major events

## Troubleshooting

### Common Issues

**Prices not changing:**
- Check scheduler is running: `price_fluctuation_scheduler.scheduler_running`
- Verify game status is IN_PROGRESS (not WAITING or PAUSED)
- Confirm bank_prices initialized in game_state
- Check logs for errors

**Prices changing too frequently:**
- Review FLUCTUATION_PROBABILITY setting (should be 0.0333)
- Check for multiple event effects stacking
- Verify momentum calculations not extreme

**Prices stuck at bounds:**
- Strong momentum + event effect can pin prices
- Mean reversion will eventually pull back
- Consider reducing event effect magnitudes

**Buy/sell spread violated:**
- Check SPREAD_PERCENTAGE (should be 0.1)
- Verify _apply_spread() logic
- Review price rounding code

## Related Documentation

- **Game Events**: `docs/game-design/GAME_EVENTS.md`
- **Trading System**: `docs/technical/TRADING_FEATURE_README.md`
- **Event Manager**: `backend/event_manager.py`
- **Pricing Manager**: `backend/pricing_manager.py`
