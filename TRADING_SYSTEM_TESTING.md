# Trading System Testing Guide

## Overview
This guide provides instructions for testing the new trading system functionality.

## Features Implemented

### 1. Dynamic Bank Pricing
- **Buy/Sell Spread**: Bank sells resources at 10% above baseline, buys at 10% below baseline
- **Supply & Demand**: Prices adjust automatically after each trade
  - When teams buy from bank: prices increase
  - When teams sell to bank: prices decrease
- **Price Bounds**: Prices can range from -50% to +100% of baseline
- **Price History**: All price changes are tracked and can be visualized

### 2. Bank Trading Interface
- **Price Chart**: Visual display of price history using Chart.js
- **Resource Selection**: Choose which resource to trade
- **Buy/Sell Toggle**: Switch between buying from bank or selling to bank
- **Trade Preview**: See the total cost/gain before confirming
- **Real-time Updates**: Prices update across all clients via WebSocket

### 3. Team-to-Team Trading
- **Create Offers**: Teams can propose trades to other teams
- **Counter-Offers**: Receiving team can counter with different terms
- **Accept/Reject**: Full negotiation workflow
- **Trade Notifications**: WebSocket updates notify teams of new offers
- **Pending Trades View**: See all active trade offers

## Manual Testing Steps

### Prerequisites
1. Start the backend server: `cd backend && python main.py`
2. Start the frontend server: `cd frontend && python3 -m http.server 3000`
3. Open browser to `http://localhost:3000`

### Test 1: Bank Trading - Basic Flow

1. **Create a Game**
   - Create new game with at least 2 teams
   - Add host, banker, and at least 2 players (one per team)
   - Assign players to different teams
   - Start the game

2. **Open Bank Trading Modal**
   - As a player, click "💰 Trade with Bank"
   - Verify the modal opens with:
     - Price history chart (should show initial prices)
     - Resource dropdown
     - Quantity input
     - Buy/Sell radio buttons
     - Trade preview section

3. **View Price Chart**
   - Select different resources from the dropdown
   - Verify chart updates to show that resource's history
   - Should see three lines: Buy Price, Sell Price, Baseline

4. **Execute a Buy Trade**
   - Select "Food" resource
   - Enter quantity: 10
   - Select "Buy from Bank"
   - Verify trade preview shows:
     - Action: Buy 10 Food from Bank
     - Unit Price (should be > baseline)
     - Total Cost
   - Click "✓ Execute Trade"
   - Verify:
     - Team loses currency
     - Team gains food
     - Success message appears
     - Price chart updates (food price should increase slightly)

5. **Execute a Sell Trade**
   - Select "Food" resource
   - Enter quantity: 5
   - Select "Sell to Bank"
   - Verify trade preview shows sell price (lower than buy price)
   - Execute trade
   - Verify:
     - Team gains currency (less than what they paid to buy)
     - Team loses food
     - Food price decreases

6. **Verify Price Dynamics**
   - Execute several buy trades of the same resource
   - Watch the price increase in the chart
   - Execute sell trades
   - Watch the price decrease
   - Verify prices stay within bounds (-50% to +100% of baseline)

### Test 2: Team-to-Team Trading

1. **Create Trade Offer**
   - As Player 1 (Team 1), click "🤝 Trade with Team"
   - Click "Create Offer" tab
   - Select target team (Team 2)
   - Click "+ Add Resource" under "You Offer"
   - Select "Food" and enter quantity: 10
   - Click "+ Add Resource" under "You Request"
   - Select "Raw Materials" and enter quantity: 15
   - Click "📤 Send Trade Offer"
   - Verify success message

2. **Receive Trade Offer**
   - As Player 2 (Team 2), open trading modal
   - Click "Pending Trades" tab
   - Verify you see the incoming trade offer:
     - Shows Team 1 → Team 2
     - Shows offered: Food: 10
     - Shows requested: Raw Materials: 15
     - Status: pending

3. **Accept Trade**
   - Click "✓ Accept" button
   - Confirm the trade
   - Verify:
     - Team 1 loses 10 food, gains 15 raw materials
     - Team 2 loses 15 raw materials, gains 10 food
     - Success message appears
     - Trade disappears from pending list
     - Event log shows "Trade completed successfully!"

4. **Test Rejection**
   - Create another trade offer
   - As receiving team, click "✗ Reject"
   - Verify trade is rejected and removed from pending list
   - Initiating team sees "Trade rejected" message

5. **Test Cancellation**
   - As initiating team, create a trade offer
   - Click "Cancel" button on your own offer
   - Verify offer is cancelled and removed

6. **Test Counter-Offer (Placeholder)**
   - Create a trade offer
   - As receiving team, click "↩️ Counter"
   - Verify counter-offer UI message appears
   - (Full counter-offer UI not yet implemented)

### Test 3: WebSocket Real-time Updates

1. **Setup**
   - Open two browser windows
   - Window 1: Player from Team 1
   - Window 2: Player from Team 2

2. **Test Bank Trade Broadcasts**
   - In Window 1, execute a bank trade
   - Verify both windows receive the update
   - Verify both windows show updated prices
   - Verify event logs in both windows

3. **Test Team Trade Notifications**
   - In Window 1, create trade offer to Team 2
   - Verify Window 2 shows notification: "📥 New trade offer from Team 1!"
   - In Window 2, accept the trade
   - Verify Window 1 shows: "✓ Trade completed successfully!"
   - Verify both windows show updated resources

### Test 4: Edge Cases

1. **Insufficient Resources**
   - Try to buy resources when you don't have enough currency
   - Verify error message: "Insufficient currency"
   - Try to sell resources you don't have
   - Verify error message

2. **Insufficient Resources for Trade Offer**
   - Try to create trade offer with resources you don't have
   - Verify error message

3. **Multiple Trades**
   - Execute many trades in quick succession
   - Verify price chart updates smoothly
   - Verify no race conditions or data corruption

4. **Price Bounds**
   - Execute many buy trades to push price to maximum
   - Verify price stops at +100% of baseline
   - Execute many sell trades
   - Verify price stops at -50% of baseline

## Expected Behavior

### Bank Pricing
- Initial prices should be close to baseline with small spread
- After buying: prices increase (more demand)
- After selling: prices decrease (more supply)
- All resources are affected by trades (secondary effect)
- Price changes are logged and visible in chart
- Spread (buy-sell difference) is maintained

### Team Trading
- Offers can be created, accepted, rejected, or cancelled
- Resources are transferred atomically (all or nothing)
- Trade validation prevents insufficient resource trades
- WebSocket events keep all clients synchronized
- Pending trades are visible to both parties

## Troubleshooting

### Backend Not Starting
- Check if port 8000 is available
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check for any import errors in console

### Frontend Not Loading
- Verify frontend server is running on port 3000
- Check browser console for JavaScript errors
- Clear browser cache if seeing old code

### Trading Features Not Appearing
- Verify game has been started (status: in_progress)
- Check that player is assigned to a team
- Check browser console for errors
- Verify WebSocket connection is active

### Price Chart Not Displaying
- Verify Chart.js loaded (check browser console)
- Check that banker role exists in game
- Verify prices were initialized when game started

## API Endpoints

### Bank Trading
- `POST /api/v2/trading/{game_code}/bank/initialize-prices` - Initialize prices
- `POST /api/v2/trading/{game_code}/bank/trade` - Execute bank trade
- `GET /api/v2/trading/{game_code}/bank/prices` - Get current prices
- `GET /api/v2/trading/{game_code}/bank/price-history` - Get price history

### Team Trading
- `POST /api/v2/trading/{game_code}/team/offer` - Create trade offer
- `POST /api/v2/trading/{game_code}/team/offer/{trade_id}/counter` - Counter-offer
- `POST /api/v2/trading/{game_code}/team/offer/{trade_id}/accept` - Accept trade
- `POST /api/v2/trading/{game_code}/team/offer/{trade_id}/reject` - Reject trade
- `POST /api/v2/trading/{game_code}/team/offer/{trade_id}/cancel` - Cancel trade
- `GET /api/v2/trading/{game_code}/team/{team_number}/offers` - Get team's trades
- `GET /api/v2/trading/{game_code}/team/offers/all` - Get all active trades

## WebSocket Events

### Bank Trading Events
- `bank_prices_initialized` - Prices initialized for game
- `bank_trade_completed` - Trade executed, includes new prices and resources

### Team Trading Events
- `trade_offer_created` - New trade offer created
- `trade_counter_offered` - Counter-offer made
- `trade_accepted` - Trade accepted and completed
- `trade_rejected` - Trade rejected
- `trade_cancelled` - Trade cancelled by initiator

## Known Limitations

1. **Counter-offer UI**: Full counter-offer interface not yet implemented (shows placeholder)
2. **Price Chart Performance**: May slow down with very long price histories (>1000 records)
3. **Mobile UI**: Trading modals may need responsive design improvements
4. **Undo**: No undo functionality for completed trades
5. **Trade History**: No persistent log of completed trades (only active trades shown)

## Future Enhancements

1. Complete counter-offer UI with inline editing
2. Trade history view for completed trades
3. Trade statistics and analytics
4. Automated price adjustments based on time
5. Special trading events (flash sales, market crashes)
6. Trading restrictions (cooldowns, limits)
7. Multi-resource bundle offers
8. Trade templates/favorites
