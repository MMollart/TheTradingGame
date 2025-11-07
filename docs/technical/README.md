# Technical Documentation

This folder contains implementation details, architecture documentation, and developer guides.

## Files in this folder:

### 🎯 Core Features

**Challenge System:**
- **[CHALLENGE_SYSTEM_README.md](CHALLENGE_SYSTEM_README.md)** - Complete challenge architecture
  - Multi-user support
  - Pause-aware timing
  - API reference
  - Testing guide
  
- **[CHALLENGE-WEBSOCKET-IMPLEMENTATION.md](CHALLENGE-WEBSOCKET-IMPLEMENTATION.md)** - WebSocket event handling
  - Real-time synchronization
  - Event types and payloads
  - Connection management
  
- **[CHALLENGE-WEBSOCKET-TESTING.md](CHALLENGE-WEBSOCKET-TESTING.md)** - Testing methodology
  - Test cases for WebSocket events
  - Integration testing
  - Debugging strategies

**Game Features:**
- **[FEATURE-LOBBY-AND-CHALLENGES.md](FEATURE-LOBBY-AND-CHALLENGES.md)** - Lobby system
  - Player approval workflow
  - Team assignment
  - Challenge request flow
  
- **[FEATURE-GAME-DURATION.md](FEATURE-GAME-DURATION.md)** - Game timer system
  - Configurable duration (1-4 hours)
  - Pause/resume behavior
  - Countdown display
  
- **[FEATURE-FOOD-TAX-AUTOMATION.md](FEATURE-FOOD-TAX-AUTOMATION.md)** - Automated food tax
  - Scheduler implementation
  - Banker controls
  - Penalty mechanics
  - Restaurant bonuses

**Trading & Building:**
- **[TRADING_FEATURE_README.md](TRADING_FEATURE_README.md)** - Trading system
  - Team-to-team trading
  - World Bank trading
  - Trade offers and acceptance
  
- **[BUILDING-CONSTRUCTION-SYSTEM.md](BUILDING-CONSTRUCTION-SYSTEM.md)** - Building mechanics
  - Building types and costs
  - Production multipliers
  - Resource requirements

### 🏗️ Implementation Summaries

- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - General patterns
  - Code conventions
  - Architecture decisions
  - Best practices
  
- **[IMPLEMENTATION_SUMMARY_FOOD_TAX.md](IMPLEMENTATION_SUMMARY_FOOD_TAX.md)** - Food tax details
  - Implementation approach
  - Key components
  - Testing strategy
  
- **[TRADING_IMPLEMENTATION_SUMMARY.md](TRADING_IMPLEMENTATION_SUMMARY.md)** - Trading implementation
  - Database schema
  - API endpoints
  - Frontend integration
  
- **[TRADING_SYSTEM_TESTING.md](TRADING_SYSTEM_TESTING.md)** - Trading tests
  - Test suite overview
  - Validation procedures
  - Edge cases

### 🔧 Setup & Configuration

- **[OSM_OAUTH_SETUP.md](OSM_OAUTH_SETUP.md)** - OAuth2 integration
  - OnlineScoutManager setup
  - Authentication flow
  - Configuration steps

### 🐛 Troubleshooting & Fixes

- **[DASHBOARD_REFRESH_FIX.md](DASHBOARD_REFRESH_FIX.md)** - Dashboard issues
  - Refresh problems
  - WebSocket reconnection
  - State synchronization
  
- **[FIX_BANKER_NOT_FOUND.md](FIX_BANKER_NOT_FOUND.md)** - Banker role bug
  - Problem description
  - Root cause analysis
  - Fix implementation

---

## Documentation by Purpose

**For New Developers:**
1. Start with [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for overview
2. Review [CHALLENGE_SYSTEM_README.md](CHALLENGE_SYSTEM_README.md) for core architecture
3. Check [CHALLENGE-WEBSOCKET-IMPLEMENTATION.md](CHALLENGE-WEBSOCKET-IMPLEMENTATION.md) for real-time features

**For Feature Development:**
1. Review relevant FEATURE-*.md files for context
2. Check IMPLEMENTATION_SUMMARY_*.md for implementation patterns
3. Follow testing guides for validation

**For Debugging:**
1. Check troubleshooting docs (DASHBOARD_REFRESH_FIX.md, FIX_BANKER_NOT_FOUND.md)
2. Review WebSocket testing guide
3. Check implementation summaries for expected behavior

**For Integration:**
1. OSM_OAUTH_SETUP.md for external authentication
2. TRADING_IMPLEMENTATION_SUMMARY.md for trading APIs
3. CHALLENGE-WEBSOCKET-IMPLEMENTATION.md for event handling

---

**Navigate back to:** [Main Documentation Index](../README.md)
