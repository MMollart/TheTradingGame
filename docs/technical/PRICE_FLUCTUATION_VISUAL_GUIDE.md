# Price Fluctuation System - Visual Guide

## System Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    PRICE FLUCTUATION SYSTEM                       │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  App Startup    │
│  (main.py)      │
└────────┬────────┘
         │
         v
┌─────────────────────────────────────┐
│  Start Price Fluctuation Scheduler  │
│  - Runs every 1 second              │
│  - Background asyncio task          │
└────────┬────────────────────────────┘
         │
         v
┌─────────────────────────────────────┐
│  For Each Active Game:              │
│  - Status = IN_PROGRESS             │
│  - Has bank_prices initialized      │
└────────┬────────────────────────────┘
         │
         v
┌─────────────────────────────────────────────────────────────┐
│              FOR EACH RESOURCE (food, materials, etc.)       │
└─────────────────────────────────────────────────────────────┘
         │
         ├─► Random Check (3.33% probability)
         │   ├─ Pass (3.33%) ──┐
         │   └─ Fail (96.67%) ─┴──► Skip to next resource
         │
         v
┌─────────────────────────────────────────────────────────────┐
│           CALCULATE PRICE CHANGE DIRECTION                   │
│                                                               │
│  1. Momentum Bias (60% weight)                               │
│     └─► Analyze last 2 minutes of price history             │
│         - Upward trend → positive bias                       │
│         - Downward trend → negative bias                     │
│                                                               │
│  2. Mean Reversion (40% weight)                              │
│     └─► Calculate distance from baseline                     │
│         - Above baseline → negative pressure                 │
│         - Below baseline → positive pressure                 │
│                                                               │
│  3. Active Event Effects                                     │
│     └─► Load from event_config.json                          │
│         - Recession: +0.3 (prices up)                        │
│         - Automation: -0.2 (prices down)                     │
│         - Drought: +0.2 (food/materials)                     │
│         - etc.                                               │
│                                                               │
│  Combined Bias = (0.6×momentum) + (0.4×reversion) + events  │
└────────┬────────────────────────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────────────────────────┐
│           APPLY BIASED RANDOM CHANGE                         │
│                                                               │
│  Base Change: Random ±2%                                     │
│                                                               │
│  If bias > 0 (upward pressure):                              │
│    └─► 50% + (bias×50%) chance to force positive            │
│                                                               │
│  If bias < 0 (downward pressure):                            │
│    └─► 50% + (|bias|×50%) chance to force negative          │
│                                                               │
│  Example: bias = +0.6 → 80% chance of increase              │
└────────┬────────────────────────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────────────────────────┐
│           VALIDATE & APPLY CONSTRAINTS                       │
│                                                               │
│  1. Clamp to bounds: 0.5x - 2.0x baseline                   │
│  2. Apply 10% buy/sell spread                               │
│  3. Re-validate bounds after spread                          │
│  4. Ensure: buy_price > sell_price                          │
│  5. Skip if constraints can't be met                        │
└────────┬────────────────────────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────────────────────────┐
│           UPDATE & BROADCAST                                 │
│                                                               │
│  1. Update game.game_state['bank_prices']                   │
│  2. Record in PriceHistory table                            │
│  3. Commit to database                                      │
│  4. Broadcast WebSocket event to all players                │
└─────────────────────────────────────────────────────────────┘
```

## Price Change Probability Matrix

```
                    Event Effect
                    -0.3  -0.2  -0.1   0.0  +0.1  +0.2  +0.3
                  ┌─────────────────────────────────────────┐
Momentum    -1.0  │  ▼▼▼  ▼▼▼  ▼▼▼  ▼▼▼  ▼▼   ▼▼   ▼     │
            -0.5  │  ▼▼▼  ▼▼   ▼▼   ▼▼   ▼    ▼    ~     │
             0.0  │  ▼▼   ▼    ▼    ~    ▲    ▲▲   ▲▲    │
            +0.5  │  ▼    ▼    ~    ▲▲   ▲▲   ▲▲▲  ▲▲▲   │
            +1.0  │  ~    ▲▲   ▲▲   ▲▲▲  ▲▲▲  ▲▲▲  ▲▲▲   │
                  └─────────────────────────────────────────┘

Legend:
  ▼▼▼ = Very likely to decrease (>75% chance)
  ▼▼  = Likely to decrease (60-75%)
  ▼   = Somewhat likely to decrease (50-60%)
  ~   = Neutral (45-55%)
  ▲   = Somewhat likely to increase (50-60%)
  ▲▲  = Likely to increase (60-75%)
  ▲▲▲ = Very likely to increase (>75% chance)
```

## Mean Reversion Over Time

```
Price
200 ┤                                         ██
    │                                      ███  ██
    │                                   ███       ██
180 ┤                                ███            ██
    │                             ███                 ███
    │                          ███                       ███
160 ┤                       ███                             ███
    │                    ███                                   ███
    │                 ███                                         ███
140 ┤              ███                                               ███
    │           ███                                                     ███
    │        ███                                                           ███
120 ┤     ███                                                                 ██
    │  ███                                                                      ██
100 ┤██────────────────── Baseline ──────────────────────────────────────────────
    │                                                                              ██
 80 ┤                                                                                ███
    │
    └───────────────────────────────────────────────────────────────────────────────►
    0min                         ~15 minutes                                    30min

Without events, prices gradually return to baseline due to mean reversion
```

## Event Effect Examples

### Economic Recession (+0.3 effect)

```
Starting Price: $100
Baseline: $100

Time →
0s:   $100  [Event triggered]
30s:  $102  ▲ (momentum + event effect)
60s:  $104  ▲ (continued upward pressure)
90s:  $106  ▲
120s: $108  ▲
150s: $107  ~ (some mean reversion)
180s: $109  ▲ (event effect dominates)
210s: $110  ▲
240s: $109  ~ [Event ends]
270s: $107  ▼ (mean reversion kicks in)
300s: $105  ▼
330s: $103  ▼
360s: $101  ▼
```

### Drought (+0.2 effect on food/raw_materials)

```
Food Price Timeline:

Normal:     $2  $2  $2  $2  [Drought starts]  $2  $2  $3  $3  $3  [Ends]  $3  $2
Materials:  $3  $3  $3  $3  [Drought starts]  $3  $4  $4  $4  $5  [Ends]  $4  $4
Electrical: $15 $15 $14 $15 [No effect]       $16 $15 $15 $14 $15         $15 $16

Only affected resources see price increases
```

## Momentum Example

```
Recent Price History (last 2 minutes):
$95 → $97 → $99 → $101 → $103 → $105

Average change: +2.1% per change
Momentum calculation: +2.1% / 5% = +0.42

Direction Bias Calculation:
  Momentum:      +0.42 × 0.6 (60% weight) = +0.252
  Mean Reversion: +0.05 × 0.4 (40% weight) = +0.020  (slightly above baseline)
  Event Effect:   +0.0 (no active events)  = +0.000
  ───────────────────────────────────────────────
  Total Bias:                                +0.272

Next change probability:
  Base: 50% chance up, 50% chance down
  With +0.272 bias: ~64% chance up, ~36% chance down

Result: Price more likely to continue rising
```

## Performance Characteristics

```
┌────────────────────────────────────────────────────────────┐
│  LOAD ANALYSIS (10 Active Games)                           │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Games:              10                                    │
│  Resources per game: 4 (food, materials, elec, med)       │
│  Total checks/sec:   40                                    │
│                                                             │
│  Probability Check:  3.33%                                 │
│  Actual changes/sec: ~1.3                                  │
│                                                             │
│  DB Operations:                                            │
│    - Reads:  40/sec (game state lookups)                  │
│    - Writes: ~1.3/sec (only when prices change)           │
│                                                             │
│  WebSocket:                                                │
│    - Broadcasts: ~0.3/sec (multiple resources can change  │
│                            in same game simultaneously)    │
│                                                             │
│  CPU Impact: Minimal (<1% on modern server)               │
│  Memory:     ~50MB for price history (1 week of data)     │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

## Configuration Tuning Guide

### Adjust Fluctuation Frequency
```python
# In PricingManager class
FLUCTUATION_PROBABILITY = 0.0333  # 3.33% = ~2 changes/minute per resource

# More volatile:
FLUCTUATION_PROBABILITY = 0.05    # 5% = ~3 changes/minute

# More stable:
FLUCTUATION_PROBABILITY = 0.02    # 2% = ~1.2 changes/minute
```

### Adjust Change Magnitude
```python
FLUCTUATION_MAGNITUDE = 0.02  # ±2%

# Larger swings:
FLUCTUATION_MAGNITUDE = 0.03  # ±3%

# Smaller swings:
FLUCTUATION_MAGNITUDE = 0.01  # ±1%
```

### Adjust Momentum vs Mean Reversion Balance
```python
MOMENTUM_WEIGHT = 0.6  # 60% momentum, 40% reversion

# More momentum (trends persist longer):
MOMENTUM_WEIGHT = 0.8  # 80% momentum, 20% reversion

# More reversion (faster return to baseline):
MOMENTUM_WEIGHT = 0.4  # 40% momentum, 60% reversion
```

### Adjust Event Effects
```json
// In event_config.json
"economic_recession": {
  "price_effect": 0.3  // +30% bias towards increases

  // Stronger effect:
  "price_effect": 0.5  // +50% bias

  // Weaker effect:
  "price_effect": 0.15 // +15% bias
}
```

## Troubleshooting Flowchart

```
┌─────────────────────────┐
│ Prices not changing?    │
└────────┬────────────────┘
         │
         v
    ┌─────────────────────────┐
    │ Is scheduler running?   │
    │ Check logs for startup  │
    └───┬─────────────────┬───┘
        │ No              │ Yes
        v                 v
    ┌─────────────┐   ┌──────────────────────┐
    │ Start       │   │ Is game IN_PROGRESS? │
    │ scheduler   │   │ (not WAITING/PAUSED) │
    └─────────────┘   └───┬──────────────┬───┘
                          │ No           │ Yes
                          v              v
                    ┌───────────┐   ┌───────────────────┐
                    │ Start     │   │ bank_prices       │
                    │ game      │   │ initialized?      │
                    └───────────┘   └───┬───────────┬───┘
                                        │ No        │ Yes
                                        v           v
                                  ┌──────────┐  ┌───────────┐
                                  │ Init via │  │ Wait for  │
                                  │ trading  │  │ ~30 checks│
                                  │ API      │  │ for first │
                                  └──────────┘  │ change    │
                                                │ (3.33%)   │
                                                └───────────┘
```

## Related Documentation

- [PRICE_FLUCTUATION_SYSTEM.md](PRICE_FLUCTUATION_SYSTEM.md) - Complete technical documentation
- [GAME_EVENTS.md](../game-design/GAME_EVENTS.md) - Game event definitions
- [TRADING_FEATURE_README.md](TRADING_FEATURE_README.md) - Trading system integration
