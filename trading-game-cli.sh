#!/bin/bash

# Trading Game CLI - Custom shell function for easy server management
# Add this to your ~/.zshrc file

# Main trading-game CLI function
trading-game() {
    local PROJECT_DIR="/Users/mattmollart/Documents/personal vscode projects/TheTradingGame"
    
    case "$1" in
        restart|r)
            echo "🔄 Restarting Trading Game servers..."
            "$PROJECT_DIR/restart-servers.sh"
            ;;
        stop|s)
            echo "🛑 Stopping Trading Game servers..."
            "$PROJECT_DIR/stop-servers.sh"
            ;;
        logs|l)
            case "$2" in
                backend|b)
                    echo "📋 Viewing backend logs (Ctrl+C to exit)..."
                    tail -f /tmp/trading-game-backend.log
                    ;;
                frontend|f)
                    echo "📋 Viewing frontend logs (Ctrl+C to exit)..."
                    tail -f /tmp/trading-game-frontend.log
                    ;;
                *)
                    echo "📋 Viewing backend logs (Ctrl+C to exit)..."
                    echo "💡 Tip: Use 'trading-game logs frontend' for frontend logs"
                    tail -f /tmp/trading-game-backend.log
                    ;;
            esac
            ;;
        status|st)
            echo "🔍 Checking Trading Game server status..."
            echo ""
            if ps aux | grep -E "python main.py" | grep -v grep > /dev/null; then
                echo "✅ Backend: Running on http://localhost:8000"
            else
                echo "❌ Backend: Not running"
            fi
            if ps aux | grep -E "python3 -m http.server 3000" | grep -v grep > /dev/null; then
                echo "✅ Frontend: Running on http://localhost:3000"
            else
                echo "❌ Frontend: Not running"
            fi
            ;;
        open|o)
            echo "🌐 Opening Trading Game in browser..."
            open "http://localhost:3000"
            ;;
        db-reset)
            echo "⚠️  Resetting database..."
            read "?Are you sure? This will delete all game data. (y/N): " confirm
            if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
                rm -f "$PROJECT_DIR/backend/trading_game.db"
                echo "✅ Database deleted. Restart servers to recreate."
            else
                echo "❌ Database reset cancelled."
            fi
            ;;
        *)
            echo "🎮 Trading Game CLI"
            echo ""
            echo "Usage: trading-game <command> [options]"
            echo "Alias: tg <command> [options]"
            echo ""
            echo "Commands:"
            echo "  restart, r          Restart both servers"
            echo "  stop, s             Stop both servers"
            echo "  status, st          Check server status"
            echo "  logs, l [target]    View logs (backend/frontend)"
            echo "  open, o             Open game in browser"
            echo "  db-reset            Reset database (WARNING: deletes data)"
            echo ""
            echo "Examples:"
            echo "  trading-game restart"
            echo "  tg r"
            echo "  tg logs backend"
            echo "  tg status"
            ;;
    esac
}

# Create short alias
alias tg='trading-game'

echo "✅ Trading Game CLI loaded! Type 'trading-game' or 'tg' to get started."
