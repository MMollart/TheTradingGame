# 🎮 Trading Game - Quick Start Guide

## Server Management Scripts

### Start/Restart Servers
```bash
./restart-servers.sh
```
This command will:
- Stop any running servers
- Start backend on `http://localhost:8000`
- Start frontend on `http://localhost:3000`
- Run both in background with logs

### Stop Servers
```bash
./stop-servers.sh
```

### View Logs
```bash
# Backend logs (API requests, errors, etc.)
tail -f /tmp/trading-game-backend.log

# Frontend logs (HTTP requests)
tail -f /tmp/trading-game-frontend.log
```

## Development Workflow

### Quick Test Cycle
```bash
# 1. Make your code changes
# 2. Restart servers
./restart-servers.sh

# 3. Test in browser at http://localhost:3000

# 4. View logs if needed
tail -f /tmp/trading-game-backend.log
```

### Manual Server Management
```bash
# Start backend only
cd backend && python main.py

# Start frontend only
cd frontend && python3 -m http.server 3000

# Stop servers manually
pkill -f "python main.py"
pkill -f "python3 -m http.server 3000"
```

## Common Tasks

### Reset Database
```bash
cd backend
rm trading_game.db
python main.py  # Will recreate database
```

### Check if Servers are Running
```bash
# Check processes
ps aux | grep -E "(python main.py|http.server 3000)" | grep -v grep

# Check ports
lsof -i :8000  # Backend
lsof -i :3000  # Frontend
```

### Test API
```bash
# Check backend is responding
curl http://localhost:8000/

# Check frontend is serving
curl http://localhost:3000/
```

## URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Then restart
./restart-servers.sh
```

### Check Logs for Errors
```bash
# Backend errors
grep -i error /tmp/trading-game-backend.log

# Frontend errors (usually fewer)
grep -i error /tmp/trading-game-frontend.log
```

### Database Issues
```bash
# Backup current database
cp backend/trading_game.db backend/trading_game.db.backup

# Reset database
rm backend/trading_game.db
./restart-servers.sh
```

## Testing Checklist

- [ ] Create game works
- [ ] Game code is displayed on dashboard
- [ ] Players can join with code
- [ ] Host sees players when they join
- [ ] Drag-and-drop team assignment works
- [ ] Role assignment works
- [ ] Guest approval works
- [ ] WebSocket updates in real-time

## Quick Commands Reference

```bash
# Everything in one place
./restart-servers.sh                    # Start/restart both servers
./stop-servers.sh                       # Stop both servers
tail -f /tmp/trading-game-backend.log   # View backend logs
tail -f /tmp/trading-game-frontend.log  # View frontend logs
rm backend/trading_game.db              # Reset database
```
