# 📚 The Trading Game - Documentation Index

Complete documentation for The Trading Game project. All documentation is up-to-date as of November 2025.

## 📖 Core Documentation

### [README.md](README.md) - **Start Here**
Complete project overview including:
- Project description and features
- Technology stack
- Installation and setup
- Quick start guide
- API endpoints reference
- Database schema
- Gameplay flow
- Testing guide
- Development workflow
- Security notes
- Deployment guide

**Audience**: All users, developers, and contributors

---

### [QUICKSTART.md](QUICKSTART.md) - **Quick Reference**
Fast reference guide for common tasks:
- Server management scripts
- Development workflow
- URL references
- Troubleshooting
- Quick commands reference

**Audience**: Developers who need quick command lookups

---

## 🎯 Feature Documentation

### [CHALLENGE_SYSTEM_README.md](CHALLENGE_SYSTEM_README.md)
Comprehensive guide to the challenge management system:
- Architecture overview (backend + frontend)
- Multi-user support
- Pause-aware timing implementation
- Database synchronization
- API reference
- Frontend ChallengeManager API
- Testing guide
- Migration from old system
- Troubleshooting
- Performance considerations

**Audience**: Developers implementing or modifying challenge features

---

### [FEATURE-GAME-DURATION.md](FEATURE-GAME-DURATION.md)
Game duration configuration feature:
- Implementation details
- Database schema changes
- API endpoints
- Frontend UI (slider component)
- Valid duration values
- Testing coverage
- Files modified

**Audience**: Developers working on game settings

---

### [FEATURE-LOBBY-AND-CHALLENGES.md](FEATURE-LOBBY-AND-CHALLENGES.md)
Lobby state management and challenge request system:
- Lobby state card visibility
- Challenge request/approval workflow
- Player experience flow
- Banker/host experience
- WebSocket events
- Challenge types and defaults
- User workflows
- Future enhancements

**Audience**: Developers working on lobby and challenge UI

---

## 🔌 Technical Documentation

### [CHALLENGE-WEBSOCKET-IMPLEMENTATION.md](CHALLENGE-WEBSOCKET-IMPLEMENTATION.md)
Real-time WebSocket synchronization:
- Architecture diagram
- WebSocket message flow
- Components modified
- Event types and payloads
- Implementation details
- Broadcasting strategies
- Multi-user synchronization

**Audience**: Developers implementing real-time features

---

### [CHALLENGE-WEBSOCKET-TESTING.md](CHALLENGE-WEBSOCKET-TESTING.md)
Testing guide for WebSocket functionality:
- Quick start testing
- Manual testing procedures
- Browser console test scripts
- Expected results
- Automated testing examples
- Integration test scenarios
- Common issues and solutions

**Audience**: QA testers, developers testing WebSocket features

---

## 🧪 Testing

### Test Suite: `backend/tests/`
- **82 passing tests** (95.3% pass rate)
- **4 skipped tests** (intentional - future features)

#### Test Files:
- `test_authentication.py` - User auth, roles, guest approval (12 tests)
- `test_challenge_manager.py` - Challenge lifecycle, pause timing (17 tests)
- `test_challenge_locking.py` - School building, simultaneous challenges (9 tests)
- `test_game_duration.py` - Duration configuration (10 tests)
- `test_game_management.py` - Game creation, team config (12 tests)
- `test_player_management.py` - Player CRUD, roles (15 tests)
- `test_team_assignment.py` - Team assignment, auto-assign (11 tests)

**Run tests**: `cd backend && pytest -v`

---

## 🛠️ Development Tools

### Server Management Scripts

#### `restart-servers.sh`
Kills existing processes and starts both backend and frontend servers.
Logs to `/tmp/trading-game-*.log`

#### `stop-servers.sh`
Stops both backend and frontend servers cleanly.

#### `trading_game_cli.py`
Python CLI tool for server management:
```bash
trading-game start    # Start servers
trading-game stop     # Stop servers
trading-game restart  # Restart servers
trading-game status   # Check server status
trading-game logs     # View logs
```

Install: `pip install -e .`

---

## 📊 API Documentation

### Interactive Documentation (Swagger)
**URL**: http://localhost:8000/docs

Auto-generated interactive API documentation with:
- All endpoints listed
- Request/response schemas
- Try-it-out functionality
- Authentication testing

### Alternative Documentation (ReDoc)
**URL**: http://localhost:8000/redoc

Clean, responsive API documentation.

---

## 🗂️ File Structure Reference

```
TheTradingGame/
├── README.md                               # Main documentation (START HERE)
├── DOCS.md                                 # This file - documentation index
├── QUICKSTART.md                           # Quick reference guide
├── CHALLENGE_SYSTEM_README.md              # Challenge system deep dive
├── FEATURE-GAME-DURATION.md                # Game duration feature
├── FEATURE-LOBBY-AND-CHALLENGES.md         # Lobby & request system
├── CHALLENGE-WEBSOCKET-IMPLEMENTATION.md   # WebSocket architecture
├── CHALLENGE-WEBSOCKET-TESTING.md          # WebSocket testing guide
│
├── backend/
│   ├── main.py                             # FastAPI app & routes
│   ├── models.py                           # Database models
│   ├── schemas.py                          # Pydantic schemas
│   ├── challenge_manager.py                # Challenge business logic
│   ├── challenge_api.py                    # Challenge API v2
│   ├── websocket_manager.py                # WebSocket connections
│   ├── game_logic.py                       # Game rules
│   ├── game_constants.py                   # Constants & config
│   └── tests/                              # Pytest test suite
│
├── frontend/
│   ├── dashboard.html                      # Main game UI
│   ├── dashboard.js                        # Game logic
│   ├── challenge-manager.js                # Challenge state manager
│   └── websocket-client.js                 # WebSocket client
│
├── restart-servers.sh                      # Server management
├── stop-servers.sh                         # Stop servers
├── trading_game_cli.py                     # CLI tool
└── pyproject.toml                          # Project config
```

---

## 🚀 Common Tasks

### First-Time Setup
1. Read [README.md](README.md) - Project overview
2. Follow installation steps in README
3. Run `./restart-servers.sh`
4. Visit http://localhost:3000
5. Create a game and test functionality

### Adding New Features
1. Review relevant feature docs above
2. Check existing tests in `backend/tests/`
3. Write tests first (TDD)
4. Implement feature
5. Run test suite: `pytest -v`
6. Update documentation

### Testing Changes
1. Run full test suite: `pytest -v`
2. Test WebSocket: Use [CHALLENGE-WEBSOCKET-TESTING.md](CHALLENGE-WEBSOCKET-TESTING.md)
3. Manual testing: Follow QUICKSTART.md
4. Check logs: `tail -f /tmp/trading-game-backend.log`

### Debugging Issues
1. Check [QUICKSTART.md](QUICKSTART.md) troubleshooting section
2. Review logs in `/tmp/trading-game-*.log`
3. Check test coverage: `pytest --cov=. --cov-report=html`
4. Use API docs: http://localhost:8000/docs

---

## 📝 Documentation Standards

### When to Update Documentation

- **README.md**: Any major feature changes, API changes, setup changes
- **QUICKSTART.md**: New commands, troubleshooting steps
- **Feature Docs**: When modifying specific features
- **DOCS.md**: When adding/removing documentation files
- **API Docs**: Automatic via FastAPI (update docstrings)

### Documentation Style

- **Clear headings**: Use emoji + hierarchy
- **Code examples**: Always include working examples
- **Audience**: Specify who the doc is for
- **Up-to-date**: Remove obsolete info immediately
- **Cross-reference**: Link to related docs

---

## 🔍 Finding Information

### "How do I...?"

| Task | Documentation |
|------|---------------|
| Set up the project | [README.md](README.md) - Getting Started |
| Start the servers | [QUICKSTART.md](QUICKSTART.md) |
| Understand challenges | [CHALLENGE_SYSTEM_README.md](CHALLENGE_SYSTEM_README.md) |
| Test WebSockets | [CHALLENGE-WEBSOCKET-TESTING.md](CHALLENGE-WEBSOCKET-TESTING.md) |
| Configure game duration | [FEATURE-GAME-DURATION.md](FEATURE-GAME-DURATION.md) |
| Fix issues | [QUICKSTART.md](QUICKSTART.md) - Troubleshooting |
| Run tests | [README.md](README.md) - Testing section |
| Understand API | http://localhost:8000/docs |
| Deploy to production | [README.md](README.md) - Deployment section |

---

## 📮 Getting Help

1. **Check documentation**: Start with this index
2. **Search docs**: Use Ctrl+F in relevant files
3. **Check logs**: `/tmp/trading-game-backend.log`
4. **Review tests**: `backend/tests/` for examples
5. **API docs**: http://localhost:8000/docs for endpoints
6. **Create issue**: GitHub Issues (if applicable)

---

**Last Updated**: November 2025  
**Documentation Version**: 1.0  
**Project Version**: 0.1.0
