# Resource Trading System - Feature Overview

## 🎯 What This Feature Does

This implementation adds a sophisticated trading system to The Trading Game, allowing:

1. **Players trade resources with the bank** at dynamic prices that change based on supply and demand
2. **Teams negotiate trades with each other** using a proposal/counter-offer system
3. **Visual price charts** help players decide when to buy or sell
4. **Real-time updates** keep all players synchronized via WebSocket

## 🚀 Quick Start

### For Developers

1. **Clone and install dependencies**:
   ```bash
   cd backend && pip install -r requirements.txt
   cd ../frontend
   ```

2. **Start servers**:
   ```bash
   ./restart-servers.sh
   # Or manually:
   # Terminal 1: cd backend && python main.py
   # Terminal 2: cd frontend && python3 -m http.server 3000
   ```

3. **Test the feature**:
   - Open http://localhost:3000
   - Create a game with at least 2 teams
   - Assign players to teams
   - Start the game
   - Click "💰 Trade with Bank" or "🤝 Trade with Team"

### For Players

**Bank Trading**:
1. Click "💰 Trade with Bank" button
2. View the price history chart to see trends
3. Select a resource and quantity
4. Choose "Buy from Bank" or "Sell to Bank"
5. Review the preview (shows total cost/gain)
6. Click "✓ Execute Trade"

**Team Trading**:
1. Click "🤝 Trade with Team" button
2. Select target team
3. Add resources you want to offer (click "+ Add Resource")
4. Add resources you want to request
5. Click "📤 Send Trade Offer"
6. The other team can accept, reject, or counter your offer

## 📊 How Dynamic Pricing Works

### Baseline Prices
Each resource has a baseline price (from `game_constants.py`):
- Food: 2 currency
- Raw Materials: 3 currency
- Electrical Goods: 15 currency
- Medical Goods: 20 currency

### Buy/Sell Spread (10%)
- **Buy Price** (bank sells): Baseline + 10% = what players pay
- **Sell Price** (bank buys): Baseline - 10% = what players receive

Example for Food (baseline = 2):
- Buy from bank: 2.2 currency per unit
- Sell to bank: 1.8 currency per unit

### Supply & Demand Adjustments
Prices automatically adjust after each trade:

**When teams buy from bank** (high demand):
- Primary resource price increases
- Other resources increase slightly (secondary effect)

**When teams sell to bank** (high supply):
- Primary resource price decreases
- Other resources decrease slightly (secondary effect)

**Price Bounds**:
- Minimum: 50% of baseline (-50%)
- Maximum: 200% of baseline (+100%)

This prevents extreme price manipulation while allowing meaningful market dynamics.

### Example Price Evolution

```
Initial Food Price:
- Buy: 2.2 | Sell: 1.8 | Baseline: 2.0

Team 1 buys 50 food:
- Buy: 2.3 | Sell: 1.9 | Baseline: 2.0 (price increased)

Team 2 sells 30 food:
- Buy: 2.2 | Sell: 1.8 | Baseline: 2.0 (price decreased)
```

## 🔄 Team Trading Workflow

### Simple Trade Flow
```
Team A creates offer:
  - Offers: 10 Food
  - Requests: 20 Raw Materials

Team B receives notification: "📥 New trade offer from Team 1!"

Team B can:
  ✓ Accept → Resources transfer immediately
  ✗ Reject → Offer cancelled
  ↩️ Counter → Propose different terms
```

### Counter-Offer Flow
```
Team A offers: 10 Food for 20 Raw Materials
Team B counters: 15 Food for 20 Raw Materials
Team A receives notification: "↩️ Counter-offer received from Team 2"
Team A can:
  ✓ Accept counter → Trade executes with new terms
  ✗ Reject → Trade cancelled
```

## 🎨 User Interface

### Bank Trade Modal
```
┌─────────────────────────────────────┐
│ 💰 Trade with Bank            [×]   │
├─────────────────────────────────────┤
│ Price History Chart                 │
│ [Food ▼]                           │
│ ╭─────────────────────────────╮    │
│ │      /\      /\              │    │
│ │     /  \    /  \   Buy Price │    │
│ │ ═══════════════════ Baseline│    │
│ │   /    \/  \/    \ Sell Price│   │
│ ╰─────────────────────────────╯    │
│                                     │
│ Resource: [Food ▼]                 │
│ Quantity: [10    ]                 │
│ ○ Buy from Bank  ● Sell to Bank   │
│                                     │
│ Trade Preview:                      │
│ • Action: Sell 10 Food to Bank    │
│ • Unit Price: 1.8 💰               │
│ • Total Gain: 18 💰                │
│                                     │
│ [✓ Execute Trade] [Cancel]        │
└─────────────────────────────────────┘
```

### Team Trade Modal
```
┌─────────────────────────────────────┐
│ 🤝 Trade with Team            [×]   │
├─────────────────────────────────────┤
│ [Create Offer] [Pending Trades]    │
├─────────────────────────────────────┤
│ Trade with: [Team 2 ▼]            │
│                                     │
│ You Offer:          You Request:   │
│ ┌─────────────┐    ┌─────────────┐│
│ │[Food ▼] [10]│    │[Raw Mat ▼]  ││
│ │[× Remove]   │    │[20 ] [× ]   ││
│ └─────────────┘    └─────────────┘│
│ [+ Add Resource]   [+ Add Resource]│
│                                     │
│ [📤 Send Trade Offer]              │
└─────────────────────────────────────┘
```

## 📡 Real-Time Updates

All trading actions broadcast WebSocket events:

| Event | Triggered When | All Players See |
|-------|---------------|-----------------|
| `bank_trade_completed` | Bank trade executes | Updated prices, event log |
| `trade_offer_created` | Team creates offer | Notification to receiving team |
| `trade_counter_offered` | Counter-offer made | Notification to original team |
| `trade_accepted` | Trade completes | Both teams see updated resources |
| `trade_rejected` | Trade declined | Both teams notified |
| `trade_cancelled` | Offer withdrawn | Both teams notified |

## 🔒 Security Features

### Validation
- ✅ Teams can't trade resources they don't have
- ✅ Bank can't sell more than its inventory
- ✅ Players can only trade for their own team
- ✅ All transactions are atomic (all-or-nothing)

### XSS Prevention
- ✅ No `innerHTML` injection
- ✅ Safe DOM manipulation using `textContent`
- ✅ Input validation on all endpoints

### CodeQL Security Scan
- ✅ **0 vulnerabilities found**
- ✅ Python code: Clean
- ✅ JavaScript code: Clean

## 📝 API Endpoints

### Bank Trading
```
POST /api/v2/trading/{game_code}/bank/initialize-prices
POST /api/v2/trading/{game_code}/bank/trade
GET  /api/v2/trading/{game_code}/bank/prices
GET  /api/v2/trading/{game_code}/bank/price-history
```

### Team Trading
```
POST /api/v2/trading/{game_code}/team/offer
POST /api/v2/trading/{game_code}/team/offer/{id}/counter
POST /api/v2/trading/{game_code}/team/offer/{id}/accept
POST /api/v2/trading/{game_code}/team/offer/{id}/reject
POST /api/v2/trading/{game_code}/team/offer/{id}/cancel
GET  /api/v2/trading/{game_code}/team/{team}/offers
GET  /api/v2/trading/{game_code}/team/offers/all
```

## 🧪 Testing

### Automated Tests
- **19 unit tests** covering:
  - Pricing algorithm
  - Trade manager logic
  - API endpoints
  - Edge cases

Run tests (requires FastAPI fix):
```bash
cd backend
pytest tests/test_trading_system.py -v
```

### Manual Testing
Follow the comprehensive guide in `TRADING_SYSTEM_TESTING.md`:
1. Bank trading basic flow
2. Price dynamics verification
3. Team trading workflow
4. WebSocket real-time updates
5. Edge cases and error handling

## 📚 Documentation

1. **TRADING_SYSTEM_TESTING.md** - Step-by-step manual testing guide
2. **TRADING_IMPLEMENTATION_SUMMARY.md** - Complete technical documentation
3. **This file** - Feature overview and user guide

## 🎓 Game Strategy Tips

### For Players

**Bank Trading**:
- 📈 Buy when prices are low (near baseline or below)
- 📉 Sell when prices are high (above baseline)
- 📊 Check the price chart to see trends
- 💡 Other teams' trades affect prices too!

**Team Trading**:
- 🤝 Negotiate for resources your nation lacks
- 💰 Consider offering currency for scarce resources
- 🔄 Use counter-offers to get better deals
- ⚡ Accept good offers quickly before prices change

### For Hosts/Bankers

**Market Manipulation**:
- Trigger events to create scarcity
- Watch which resources are most traded
- Adjust starting inventories to balance gameplay

## 🐛 Known Issues

1. **Test Execution**: FastAPI/Pydantic version mismatch
   - Tests are written but can't run automatically
   - Manual testing recommended

## 🚀 Future Enhancements

### Short-term
- [x] Complete counter-offer UI ✅ (Implemented)
- [ ] Trade history view (completed trades)
- [ ] Mobile-responsive modals
- [ ] Price trend indicators (↑↓ arrows)

### Long-term
- [ ] Trade analytics dashboard
- [ ] Automated market events (flash sales, crashes)
- [ ] Trading cooldowns and limits
- [ ] Multi-resource bundle offers
- [ ] Trade templates/favorites
- [ ] AI price recommendations

## 🤝 Contributing

When modifying the trading system:

1. **Backend changes**: Update both `pricing_manager.py` and `trade_manager.py`
2. **Frontend changes**: Update both `trading-manager.js` and `dashboard.js`
3. **New events**: Add WebSocket handler in `handleGameEvent()`
4. **Price algorithm**: Modify parameters in `PricingManager` class
5. **Test changes**: Add tests to `test_trading_system.py`

## 📞 Support

Issues or questions:
- Check `TRADING_SYSTEM_TESTING.md` for troubleshooting
- Review browser console for JavaScript errors
- Check backend logs for API errors
- Verify WebSocket connection is active

## 📜 License

This feature is part of The Trading Game project. See main repository for license details.

---

**Built with ❤️ for The Trading Game**
