# 📚 The Trading Game Documentation

Complete documentation for The Trading Game - a real-time multiplayer resource trading and building simulation.

## 📂 Documentation Structure

Documentation is organized into three main categories:

- **[game-design/](game-design/)** - Game mechanics, events, scenarios, and design documents
- **[player-guides/](player-guides/)** - Player instructions, quickstart guides, and printing resources
- **[technical/](technical/)** - Implementation details, architecture, fixes, and developer guides

---

## � Quick Navigation

### 🎮 Game Design Documentation
Understand the game mechanics and create new content:

- **[CHATGPT_GAME_PROMPT.md](game-design/CHATGPT_GAME_PROMPT.md)** - 🤖 Complete game description for AI assistance
- **[EVENT_SYSTEM.md](game-design/EVENT_SYSTEM.md)** - 🎲 **Game Events System** - Complete guide to 8 event types with difficulty scaling and API usage
- **[GAME_EVENTS.md](game-design/GAME_EVENTS.md)** - 🌪️ Detailed event documentation with formulas and implementation notes
- **[HISTORICAL_SCENARIOS.md](game-design/HISTORICAL_SCENARIOS.md)** - 🎭 6 historical scenarios with themed nations and rules
- **[FLOW_DIAGRAM.md](game-design/FLOW_DIAGRAM.md)** - 📊 Game flow diagrams and state transitions
- **[SCOUT_COLORS.md](game-design/SCOUT_COLORS.md)** - 🎨 Scout-themed color palette and design system

### 📚 Player Guides
Everything players and hosts need to play:

- **[PLAYER_INSTRUCTIONS_QUICK.md](player-guides/PLAYER_INSTRUCTIONS_QUICK.md)** - 📄 **2-page quick reference (BEST for printing!)**
- **[PLAYER_INSTRUCTIONS.md](player-guides/PLAYER_INSTRUCTIONS.md)** - 📋 Complete gameplay guide (detailed reference)
- **[QUICKSTART.md](player-guides/QUICKSTART.md)** - ⚡ Quick reference for server management and common commands
- **[FOOD-TAX-QUICKSTART.md](player-guides/FOOD-TAX-QUICKSTART.md)** - 🍔 Quick guide to food tax feature usage
- **[PRINTING_GUIDE.md](player-guides/PRINTING_GUIDE.md)** - 🖨️ Guide for printing player instructions

### 🔧 Technical Documentation
Implementation details for developers:

**Features & Architecture:**
- **[CHALLENGE_SYSTEM_README.md](technical/CHALLENGE_SYSTEM_README.md)** - Challenge system architecture and design
- **[CHALLENGE-WEBSOCKET-IMPLEMENTATION.md](technical/CHALLENGE-WEBSOCKET-IMPLEMENTATION.md)** - WebSocket event handling
- **[CHALLENGE-WEBSOCKET-TESTING.md](technical/CHALLENGE-WEBSOCKET-TESTING.md)** - Testing guide for WebSocket events
- **[EVENT_SYSTEM_IMPLEMENTATION.md](technical/EVENT_SYSTEM_IMPLEMENTATION.md)** - **Event system backend** - Architecture, API endpoints, and integration
- **[FEATURE-GAME-DURATION.md](technical/FEATURE-GAME-DURATION.md)** - Configurable game duration (1-4 hours)
- **[FEATURE-LOBBY-AND-CHALLENGES.md](technical/FEATURE-LOBBY-AND-CHALLENGES.md)** - Lobby system and challenge mechanics
- **[FEATURE-FOOD-TAX-AUTOMATION.md](technical/FEATURE-FOOD-TAX-AUTOMATION.md)** - Automated food tax system
- **[FEATURE-KINDNESS-SCORING.md](FEATURE-KINDNESS-SCORING.md)** - 🤝 Kindness-based trading score rewards cooperative behavior
- **[BUILDING-CONSTRUCTION-SYSTEM.md](technical/BUILDING-CONSTRUCTION-SYSTEM.md)** - Building mechanics and construction rules
- **[TRADING_FEATURE_README.md](technical/TRADING_FEATURE_README.md)** - Resource trading system documentation

**Implementation Summaries:**
- **[IMPLEMENTATION_SUMMARY.md](technical/IMPLEMENTATION_SUMMARY.md)** - General implementation overview
- **[IMPLEMENTATION_SUMMARY_FOOD_TAX.md](technical/IMPLEMENTATION_SUMMARY_FOOD_TAX.md)** - Food tax implementation details
- **[TRADING_IMPLEMENTATION_SUMMARY.md](technical/TRADING_IMPLEMENTATION_SUMMARY.md)** - Trading system implementation guide
- **[TRADING_SYSTEM_TESTING.md](technical/TRADING_SYSTEM_TESTING.md)** - Trading system test suite

**Setup & Troubleshooting:**
- **[OSM_OAUTH_SETUP.md](technical/OSM_OAUTH_SETUP.md)** - OnlineScoutManager OAuth2 integration guide
- **[DASHBOARD_REFRESH_FIX.md](technical/DASHBOARD_REFRESH_FIX.md)** - Dashboard refresh issues and solutions
- **[FIX_BANKER_NOT_FOUND.md](technical/FIX_BANKER_NOT_FOUND.md)** - Banker role detection bug fix

---

## � Documentation by Audience

### For Players
Learn how to play the game:
1. **[PLAYER_INSTRUCTIONS_QUICK.md](player-guides/PLAYER_INSTRUCTIONS_QUICK.md)** - 📄 **2-page quick reference (BEST for printing!)**
2. **[PLAYER_INSTRUCTIONS.md](player-guides/PLAYER_INSTRUCTIONS.md)** - 📋 Complete gameplay guide (detailed reference)
3. [FEATURE-LOBBY-AND-CHALLENGES.md](technical/FEATURE-LOBBY-AND-CHALLENGES.md) - Challenge mechanics deep-dive
4. [TRADING_FEATURE_README.md](technical/TRADING_FEATURE_README.md) - Trading system details

### For Game Hosts
Start here to run games:
1. [QUICKSTART.md](player-guides/QUICKSTART.md) - Start servers and basic commands
2. [FEATURE-GAME-DURATION.md](technical/FEATURE-GAME-DURATION.md) - Setting game duration
3. [FOOD-TAX-QUICKSTART.md](player-guides/FOOD-TAX-QUICKSTART.md) - Managing food tax
4. [EVENT_SYSTEM.md](game-design/EVENT_SYSTEM.md) - **Triggering game events** - Complete guide to 8 event types with API examples

### For Developers
Technical references for contributors:
1. [DOCS.md](DOCS.md) - API and technical overview
2. [CHALLENGE_SYSTEM_README.md](technical/CHALLENGE_SYSTEM_README.md) - Challenge architecture
3. [CHALLENGE-WEBSOCKET-IMPLEMENTATION.md](technical/CHALLENGE-WEBSOCKET-IMPLEMENTATION.md) - Real-time events
4. [IMPLEMENTATION_SUMMARY.md](technical/IMPLEMENTATION_SUMMARY.md) - Implementation patterns

### For System Admins
Deployment and troubleshooting:
1. [OSM_OAUTH_SETUP.md](technical/OSM_OAUTH_SETUP.md) - External integrations
2. [DASHBOARD_REFRESH_FIX.md](technical/DASHBOARD_REFRESH_FIX.md) - Common issues
3. [FIX_BANKER_NOT_FOUND.md](technical/FIX_BANKER_NOT_FOUND.md) - Role debugging

### For Game Designers
Creating new content:
1. [CHATGPT_GAME_PROMPT.md](game-design/CHATGPT_GAME_PROMPT.md) - Use ChatGPT for game design help
2. [EVENT_SYSTEM.md](game-design/EVENT_SYSTEM.md) - **Event system** - Designing and balancing game events
3. [GAME_EVENTS.md](game-design/GAME_EVENTS.md) - Detailed event formulas and implementation notes
4. [HISTORICAL_SCENARIOS.md](game-design/HISTORICAL_SCENARIOS.md) - Scenario design patterns

### Feature Deep-Dives
Detailed feature documentation:
- **Game Duration**: [FEATURE-GAME-DURATION.md](technical/FEATURE-GAME-DURATION.md)
- **Food Tax**: [FEATURE-FOOD-TAX-AUTOMATION.md](technical/FEATURE-FOOD-TAX-AUTOMATION.md) + [FOOD-TAX-QUICKSTART.md](player-guides/FOOD-TAX-QUICKSTART.md)
- **Trading**: [TRADING_FEATURE_README.md](technical/TRADING_FEATURE_README.md) + [TRADING_IMPLEMENTATION_SUMMARY.md](technical/TRADING_IMPLEMENTATION_SUMMARY.md)
- **Kindness Scoring**: [FEATURE-KINDNESS-SCORING.md](FEATURE-KINDNESS-SCORING.md)
- **Building**: [BUILDING-CONSTRUCTION-SYSTEM.md](technical/BUILDING-CONSTRUCTION-SYSTEM.md)
- **Challenges**: [CHALLENGE_SYSTEM_README.md](technical/CHALLENGE_SYSTEM_README.md)
- **Events**: [EVENT_SYSTEM.md](game-design/EVENT_SYSTEM.md) + [EVENT_SYSTEM_IMPLEMENTATION.md](technical/EVENT_SYSTEM_IMPLEMENTATION.md) + [GAME_EVENTS.md](game-design/GAME_EVENTS.md)

## 🔍 Quick Links

- **Main README**: [../README.md](../README.md) - Project overview and installation
- **API Documentation**: http://localhost:8000/docs (when running locally)
- **Test Documentation**: [../backend/tests/README.md](../backend/tests/README.md)

## 📝 Documentation Standards

When contributing documentation:
1. Use clear, descriptive headings
2. Include code examples where relevant
3. Add screenshots for UI features
4. Keep technical jargon minimal
5. Cross-reference related documents
6. Update this index when adding new docs

## 🆕 Latest Documentation Updates

- **🤝 Kindness-Based Scoring** - Rewards generous trading with score bonuses (see [FEATURE-KINDNESS-SCORING.md](FEATURE-KINDNESS-SCORING.md))
- **🎲 Game Events System** - NEW comprehensive guides: [EVENT_SYSTEM.md](game-design/EVENT_SYSTEM.md) and [EVENT_SYSTEM_IMPLEMENTATION.md](technical/EVENT_SYSTEM_IMPLEMENTATION.md)
  - 8 event types (natural disasters, economic events, positive events)
  - Difficulty scaling and severity levels (1-5)
  - Mitigation mechanics with optional buildings
  - Integration with food tax cycles
  - Full API reference and WebSocket events
- **Game Duration Feature** - Configurable 1-4 hour gameplay
- **Food Tax Automation** - Banker-controlled tax system
- **Challenge WebSocket Events** - Real-time synchronization
- **Trading System** - Team-to-team and bank trading

---

**Need help?** Start with [QUICKSTART.md](QUICKSTART.md) or check the main [README.md](../README.md) for contact information.
