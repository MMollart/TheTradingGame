# Trading System Implementation Summary

## Overview
This implementation adds comprehensive resource trading functionality to The Trading Game, including dynamic bank pricing with supply/demand mechanics and team-to-team trade negotiation.

## Key Features

### 1. Dynamic Bank Pricing System
**Location**: `backend/pricing_manager.py`

- **Buy/Sell Spread**: 10% spread between buy and sell prices
  - Bank sells resources at higher price (buy_price)
  - Bank buys resources at lower price (sell_price)
  - Baseline price serves as reference point

- **Supply & Demand Adjustments**:
  - Prices adjust after each trade based on direction and quantity
  - Team buying from bank → prices increase (demand up)
  - Team selling to bank → prices decrease (supply up)
  - Adjustment factor: 5% per 100 units traded
  - Secondary effect: All resources adjust slightly (20% of primary effect)

- **Price Bounds**:
  - Minimum: 50% of baseline (-50%)
  - Maximum: 200% of baseline (+100%)
  - Prevents extreme price fluctuations

- **Price History Tracking**:
  - All price changes recorded in database
  - Timestamped records for charting
  - Tracks both trade-triggered and manual updates

### 2. Team-to-Team Trading System
**Location**: `backend/trade_manager.py`

- **Trade Offer Workflow**:
  1. Team A creates offer (what they give vs what they want)
  2. Team B can accept, reject, or counter-offer
  3. If counter-offered, Team A can accept the counter or reject
  4. Trade executes atomically (all resources transferred at once)

- **Validation**:
  - Checks team has sufficient resources before creating offer
  - Re-validates resources before executing trade
  - Prevents trading with your own team
  - Ensures only appropriate players can take actions

- **Trade States**:
  - `PENDING`: Initial offer, awaiting response
  - `COUNTER_OFFERED`: Counter-offer made
  - `ACCEPTED`: Trade completed
  - `REJECTED`: Trade declined
  - `CANCELLED`: Offer withdrawn by initiator

### 3. Database Models
**Location**: `backend/models.py`

#### TradeOffer Model
```python
- id: Primary key
- game_session_id: Foreign key to game
- from_team_number: Initiating team
- to_team_number: Receiving team
- initiated_by_player_id: Player who created offer
- offered_resources: JSON dict of resources offered
- requested_resources: JSON dict of resources requested
- counter_offered_resources: JSON dict (nullable)
- counter_requested_resources: JSON dict (nullable)
- counter_offered_by_player_id: Foreign key (nullable)
- status: TradeOfferStatus enum
- created_at, updated_at, completed_at: Timestamps
```

#### PriceHistory Model
```python
- id: Primary key
- game_session_id: Foreign key to game
- resource_type: String (food, raw_materials, etc.)
- buy_price: Integer (bank sells at this price)
- sell_price: Integer (bank buys at this price)
- baseline_price: Integer (reference price)
- timestamp: DateTime (indexed for queries)
- triggered_by_trade: Boolean (manual vs automatic update)
```

### 4. REST API Endpoints
**Location**: `backend/trading_api.py`

#### Bank Trading
- `POST /api/v2/trading/{game_code}/bank/initialize-prices`
  - Initialize prices when game starts
  - Returns price structure for all resources

- `POST /api/v2/trading/{game_code}/bank/trade`
  - Execute a bank trade
  - Request body: resource_type, quantity, is_buying, team_number, player_id
  - Updates prices automatically after trade
  - Broadcasts new prices via WebSocket

- `GET /api/v2/trading/{game_code}/bank/prices`
  - Get current bank prices
  - Returns all resources with buy/sell/baseline prices

- `GET /api/v2/trading/{game_code}/bank/price-history`
  - Get price history for charting
  - Query params: resource_type (optional), limit (default 100)
  - Returns array of historical price records

#### Team Trading
- `POST /api/v2/trading/{game_code}/team/offer`
  - Create new trade offer
  - Validates resources available

- `POST /api/v2/trading/{game_code}/team/offer/{trade_id}/counter`
  - Create counter-offer
  - Only receiving team can counter

- `POST /api/v2/trading/{game_code}/team/offer/{trade_id}/accept`
  - Accept trade (original or counter)
  - Executes resource transfer atomically
  - Query param: accept_counter (boolean)

- `POST /api/v2/trading/{game_code}/team/offer/{trade_id}/reject`
  - Reject trade offer
  - Only receiving team can reject

- `POST /api/v2/trading/{game_code}/team/offer/{trade_id}/cancel`
  - Cancel trade offer
  - Only initiator can cancel

- `GET /api/v2/trading/{game_code}/team/{team_number}/offers`
  - Get all offers involving a team
  - Query param: include_completed (boolean)

- `GET /api/v2/trading/{game_code}/team/offers/all`
  - Get all active trades (for host/banker view)

### 5. Frontend Trading Manager
**Location**: `frontend/trading-manager.js`

JavaScript class that handles:
- Bank price loading and caching
- Price history fetching and chart rendering
- Bank trade execution
- Team trade offer CRUD operations
- Resource formatting and display helpers

Key Methods:
- `initialize()`: Load initial prices and trades
- `executeBankTrade()`: Execute bank transaction
- `renderPriceChart()`: Create Chart.js visualization
- `createTradeOffer()`: Submit new trade offer
- `acceptTrade()`, `rejectTrade()`, `cancelTrade()`: Trade actions

### 6. Frontend UI Components
**Location**: `frontend/dashboard.html`, `frontend/dashboard.js`

#### Bank Trade Modal
- Price history chart with Chart.js
- Resource dropdown selector
- Quantity input
- Buy/Sell toggle
- Trade preview (shows cost/gain before execution)
- Execute and cancel buttons

#### Team Trade Modal
- Two tabs: "Create Offer" and "Pending Trades"
- Create Offer Tab:
  - Target team selector
  - Dynamic resource input groups (add/remove)
  - Separate sections for offering and requesting
  - Send offer button
- Pending Trades Tab:
  - List of all active trades
  - Shows offer details and counter-offers
  - Accept/Reject/Cancel buttons based on role
  - Status badges

### 7. WebSocket Integration
**Location**: `frontend/dashboard.js` (handleGameEvent function)

New Events:
- `bank_prices_initialized`: Prices set up for game
- `bank_trade_completed`: Trade executed, updates resources and prices
- `trade_offer_created`: New offer notification
- `trade_counter_offered`: Counter-offer notification
- `trade_accepted`: Trade completed, updates resources
- `trade_rejected`: Trade declined
- `trade_cancelled`: Offer withdrawn

All events trigger:
- UI updates (resource displays, trade lists)
- Event log messages
- Modal refreshes if open
- Team state synchronization

### 8. CSS Styling
**Location**: `frontend/dashboard-styles.css`

New styles for:
- Trade modals (bank and team)
- Price chart container
- Trade preview section
- Trade offer cards
- Resource input groups
- Tab navigation
- Form groups and inputs
- Modal actions (button groups)
- Responsive badges and status indicators

## Integration Points

### Game Start Sequence
When game starts (`/games/{game_code}/start`):
1. Initialize team resources and buildings
2. Initialize banker state
3. **NEW**: Initialize bank prices via PricingManager
4. Store prices in banker's player_state
5. Broadcast game_status_changed event

### Team State Management
Team resources stored in: `GameSession.game_state['teams'][team_number]['resources']`

Bank prices stored in: `Player.player_state['bank_prices']` (banker role)

Trade offers stored in: `TradeOffer` table

### Resource Transfer
All resource transfers use SQLAlchemy transactions:
- Validate resources available
- Deduct from source
- Add to destination
- Mark game_state as modified with `flag_modified()`
- Commit transaction
- Broadcast update via WebSocket

## Testing

### Unit Tests
**Location**: `backend/tests/test_trading_system.py`

Test coverage includes:
- `TestPricingManager`: 8 tests
  - Price initialization
  - Spread calculation
  - Price adjustments (buy/sell)
  - Price bounds enforcement
  - Trade cost calculation
  - Price history retrieval

- `TestTradeManager`: 8 tests
  - Trade offer creation
  - Insufficient resource validation
  - Counter-offer creation
  - Trade acceptance and execution
  - Trade rejection
  - Trade cancellation
  - Trade listing

- `TestTradingAPI`: 3 tests
  - API endpoint integration tests
  - Price initialization endpoint
  - Trade offer creation endpoint

Total: **19 test cases** covering core functionality

### Manual Testing
**Location**: `TRADING_SYSTEM_TESTING.md`

Comprehensive manual testing guide covering:
- Bank trading basic flow
- Price dynamics verification
- Team-to-team trading workflow
- WebSocket real-time updates
- Edge cases and error handling

## File Manifest

### Backend Files (Python)
- `backend/models.py` - Added TradeOffer, PriceHistory models
- `backend/pricing_manager.py` - NEW: Dynamic pricing logic
- `backend/trade_manager.py` - NEW: Team trading logic
- `backend/trading_api.py` - NEW: REST API endpoints
- `backend/main.py` - Modified: Import trading router, initialize prices
- `backend/tests/test_trading_system.py` - NEW: Comprehensive tests

### Frontend Files (JavaScript/HTML/CSS)
- `frontend/trading-manager.js` - NEW: Trading client logic
- `frontend/dashboard.html` - Modified: Added trading modals, Chart.js
- `frontend/dashboard.js` - Modified: Trading UI functions, WebSocket handlers
- `frontend/dashboard-styles.css` - Modified: Added trading styles
- `frontend/game-api.js` - No changes needed (uses fetch directly)

### Documentation
- `TRADING_SYSTEM_TESTING.md` - NEW: Manual testing guide
- `TRADING_IMPLEMENTATION_SUMMARY.md` - NEW: This file

## Dependencies

### New Dependencies
- **Chart.js 4.4.0** (frontend): Price history visualization
  - Loaded via CDN in dashboard.html
  - No npm installation required

### Existing Dependencies (unchanged)
- FastAPI, SQLAlchemy, WebSockets (backend)
- Vanilla JavaScript (no framework changes)

## Configuration

### Price Parameters
In `PricingManager`:
- `MIN_MULTIPLIER = 0.5` (price can drop to 50% of baseline)
- `MAX_MULTIPLIER = 2.0` (price can rise to 200% of baseline)
- `SPREAD_PERCENTAGE = 0.1` (10% spread between buy/sell)
- `TRADE_IMPACT_FACTOR = 0.05` (5% price change per significant trade)

These can be adjusted for different game balance.

### Baseline Prices
In `game_constants.py` (`BANK_INITIAL_PRICES`):
- Food: 2 currency
- Raw Materials: 3 currency
- Electrical Goods: 15 currency
- Medical Goods: 20 currency

## Performance Considerations

### Database Queries
- Price history queries limited to 100 records by default
- Indexed timestamp column for efficient querying
- Trade offers filtered by game and status for performance

### WebSocket Broadcasts
- Targeted broadcasts to specific game only
- Efficient JSON serialization
- No broadcast storms (one message per trade)

### Frontend
- Chart.js handles large datasets efficiently
- Trade list limited to active trades by default
- Lazy loading of price history (on-demand)

## Security Considerations

### Validation
- All trades validate sufficient resources
- Player ownership verified before actions
- Team membership checked for trade actions
- No client-side resource manipulation

### Race Conditions
- SQLAlchemy transactions ensure atomicity
- Database constraints prevent duplicate trades
- Flag_modified() ensures state consistency

### Input Validation
- Quantity validation (positive integers)
- Resource type validation (known types only)
- Game code normalization (uppercase)
- Player/team ID validation

## Known Limitations

1. **Counter-offer UI**: Placeholder message shown, full UI not implemented
2. **Trade History**: Completed trades not persistently displayed
3. **Price Chart**: May slow down with extremely long histories (>1000 records)
4. **Mobile UI**: Trading modals may need responsive improvements
5. **Undo**: No rollback for completed trades

## Future Enhancements

### Short-term
- Complete counter-offer UI with inline editing
- Trade history view (completed trades log)
- Mobile-responsive modal design
- Price trend indicators (up/down arrows)

### Long-term
- Trade analytics dashboard
- Automated market events (flash sales, crashes)
- Trading cooldowns and limits
- Multi-resource bundle offers
- Trade templates/favorites
- AI-powered price recommendations

## Breaking Changes

None. This is a new feature that:
- Adds new endpoints (no existing endpoints modified)
- Extends existing models (no schema breaking changes)
- Adds UI elements (no existing UI removed)
- Is backward compatible with existing games

## Migration

No database migration required if using SQLite (auto-creates tables).

For production PostgreSQL:
```bash
# Add new tables
CREATE TABLE trade_offers (...);
CREATE TABLE price_history (...);
```

## Deployment Notes

1. No environment variable changes needed
2. No new external services required
3. Chart.js loaded via CDN (no build step)
4. Backward compatible with existing games
5. New games automatically get trading features

## Support

For issues or questions:
- See `TRADING_SYSTEM_TESTING.md` for troubleshooting
- Check browser console for JavaScript errors
- Check backend logs for API errors
- Verify WebSocket connection is active
