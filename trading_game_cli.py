#!/usr/bin/env python3
"""
Trading Game CLI - Server management tool for The Trading Game.

Provides convenient commands for starting, stopping, and managing
the Trading Game servers during development and testing.
"""

import sys
import subprocess
import signal
import time
import os
from pathlib import Path


# Project directory (parent of this script)
PROJECT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = PROJECT_DIR / "backend"
FRONTEND_DIR = PROJECT_DIR / "frontend"
DB_FILE = BACKEND_DIR / "trading_game.db"


def find_process_pids(pattern):
    """Find PIDs of processes matching the pattern."""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        pids = []
        for line in result.stdout.splitlines():
            if pattern in line and "grep" not in line:
                parts = line.split()
                if len(parts) > 1:
                    pids.append(parts[1])
        return pids
    except Exception as e:
        print(f"Error finding processes: {e}")
        return []


def stop_servers():
    """Stop both backend and frontend servers."""
    print("🛑 Stopping Trading Game servers...")
    
    # Find and kill backend processes
    backend_pids = find_process_pids("python main.py")
    if backend_pids:
        for pid in backend_pids:
            try:
                os.kill(int(pid), signal.SIGTERM)
                print(f"  ✓ Stopped backend (PID {pid})")
            except ProcessLookupError:
                pass
    else:
        print("  • Backend not running")
    
    # Find and kill frontend processes
    frontend_pids = find_process_pids("http.server 3000")
    if frontend_pids:
        for pid in frontend_pids:
            try:
                os.kill(int(pid), signal.SIGTERM)
                print(f"  ✓ Stopped frontend (PID {pid})")
            except ProcessLookupError:
                pass
    else:
        print("  • Frontend not running")
    
    print("✅ Servers stopped")


def start_servers():
    """Start both backend and frontend servers."""
    print("🚀 Starting Trading Game servers...")
    
    # Start backend
    backend_log = "/tmp/trading-game-backend.log"
    backend_process = subprocess.Popen(
        ["python", "main.py"],
        cwd=str(BACKEND_DIR),
        stdout=open(backend_log, "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    print(f"  ✓ Backend started (PID {backend_process.pid})")
    print(f"    Logs: {backend_log}")
    
    # Start frontend
    frontend_log = "/tmp/trading-game-frontend.log"
    frontend_process = subprocess.Popen(
        ["python", "-m", "http.server", "3000"],
        cwd=str(FRONTEND_DIR),
        stdout=open(frontend_log, "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    print(f"  ✓ Frontend started (PID {frontend_process.pid})")
    print(f"    Logs: {frontend_log}")
    
    # Wait a moment for servers to start
    time.sleep(1)
    
    print("\n✅ Servers running!")
    print("   Backend:  http://localhost:8000")
    print("   Frontend: http://localhost:3000")
    print("\nView logs:")
    print(f"   tail -f {backend_log}")
    print(f"   tail -f {frontend_log}")


def restart_servers():
    """Restart both servers."""
    stop_servers()
    time.sleep(1)
    start_servers()


def status():
    """Check if servers are running."""
    print("📊 Trading Game Server Status\n")
    
    # Check backend
    backend_pids = find_process_pids("python main.py")
    if backend_pids:
        print(f"✅ Backend running (PID: {', '.join(backend_pids)})")
        print("   URL: http://localhost:8000")
    else:
        print("❌ Backend not running")
    
    # Check frontend
    frontend_pids = find_process_pids("http.server 3000")
    if frontend_pids:
        print(f"✅ Frontend running (PID: {', '.join(frontend_pids)})")
        print("   URL: http://localhost:3000")
    else:
        print("❌ Frontend not running")


def view_logs(server=None):
    """View server logs."""
    backend_log = "/tmp/trading-game-backend.log"
    frontend_log = "/tmp/trading-game-frontend.log"
    
    if server == "backend" or server == "b":
        print(f"📋 Viewing backend logs: {backend_log}")
        subprocess.run(["tail", "-f", backend_log])
    elif server == "frontend" or server == "f":
        print(f"📋 Viewing frontend logs: {frontend_log}")
        subprocess.run(["tail", "-f", frontend_log])
    else:
        print(f"📋 Viewing backend logs: {backend_log}")
        subprocess.run(["tail", "-f", backend_log])


def open_browser():
    """Open the game in default browser."""
    print("🌐 Opening Trading Game in browser...")
    subprocess.run(["open", "http://localhost:3000"])


def reset_database():
    """Reset the database with confirmation."""
    print("⚠️  WARNING: This will delete all game data!")
    response = input("Are you sure you want to reset the database? (yes/no): ")
    
    if response.lower() == "yes":
        if DB_FILE.exists():
            DB_FILE.unlink()
            print("✅ Database deleted")
            print("   It will be recreated when the backend starts")
        else:
            print("ℹ️  Database file not found (already deleted)")
    else:
        print("❌ Database reset cancelled")


def print_help():
    """Print help information."""
    help_text = """
Trading Game CLI - Server management tool

Usage:
  trading-game <command> [options]
  tg <command> [options]

Commands:
  restart, r          Restart both servers
  stop, s             Stop both servers
  start               Start both servers
  status, st          Check server status
  logs, l [server]    View server logs (backend|frontend)
  open, o             Open game in browser
  db-reset            Reset database (with confirmation)
  help, h             Show this help message

Examples:
  trading-game restart       # Restart both servers
  tg r                       # Same as above (short alias)
  tg status                  # Check if servers are running
  tg logs backend            # View backend logs
  tg l b                     # Same as above (short aliases)
  tg open                    # Open game in browser
  tg db-reset                # Reset database

Log files:
  Backend:  /tmp/trading-game-backend.log
  Frontend: /tmp/trading-game-frontend.log

URLs:
  Backend:  http://localhost:8000
  Frontend: http://localhost:3000
"""
    print(help_text)


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    if command in ["restart", "r"]:
        restart_servers()
    elif command in ["stop", "s"]:
        stop_servers()
    elif command == "start":
        start_servers()
    elif command in ["status", "st"]:
        status()
    elif command in ["logs", "l"]:
        server = sys.argv[2] if len(sys.argv) > 2 else None
        view_logs(server)
    elif command in ["open", "o"]:
        open_browser()
    elif command == "db-reset":
        reset_database()
    elif command in ["help", "h", "--help", "-h"]:
        print_help()
    else:
        print(f"Unknown command: {command}")
        print("Run 'trading-game help' for usage information")
        sys.exit(1)


if __name__ == "__main__":
    main()
