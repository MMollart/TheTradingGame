# 🎮 Trading Game CLI Installation

## Quick Setup

Add the Trading Game CLI to your shell by adding this line to your `~/.zshrc`:

```bash
# Trading Game CLI Setup

This document explains how to install and use the Trading Game CLI.

## Installation

The Trading Game CLI is installed as a Python package using pip. From the project directory, run:

```bash
cd "/Users/mattmollart/Documents/personal vscode projects/TheTradingGame"
pip install -e .
```

This will install the CLI and make it available as both `trading-game` and `tg` commands from anywhere in your terminal.

## Commands

The CLI provides the following commands:

| Command | Short Alias | Description |
|---------|-------------|-------------|
| `trading-game restart` | `tg r` | Restart both backend and frontend servers |
| `trading-game start` | - | Start both servers |
| `trading-game stop` | `tg s` | Stop both servers |
| `trading-game status` | `tg st` | Check if servers are running |
| `trading-game logs [server]` | `tg l [b\|f]` | View server logs (backend or frontend) |
| `trading-game open` | `tg o` | Open the game in your default browser |
| `trading-game db-reset` | - | Reset the database (with confirmation) |
| `trading-game help` | `tg h` | Show help message |

## Usage Examples

```bash
# Restart servers
trading-game restart
# or
tg r

# Check status
tg status

# View backend logs
tg logs backend
# or
tg l b

# View frontend logs
tg logs frontend
# or
tg l f

# Open in browser
tg open

# Reset database
tg db-reset
```

## Log Files

Logs are stored in:
- Backend: `/tmp/trading-game-backend.log`
- Frontend: `/tmp/trading-game-frontend.log`

## Verification

After installation, verify the CLI is available:

```bash
# Check if installed
which trading-game
which tg

# View help
trading-game help
```

The CLI should appear in your workspace Python CLIs list in the terminal header.

## Uninstall

To remove the CLI:

```bash
pip uninstall trading-game
```
```

Then reload your shell:
```bash
source ~/.zshrc
```

## Usage

Once installed, you can use either `trading-game` or the short alias `tg`:

### Available Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `trading-game restart` | `tg r` | Restart both backend and frontend servers |
| `trading-game stop` | `tg s` | Stop both servers |
| `trading-game status` | `tg st` | Check if servers are running |
| `trading-game logs` | `tg l` | View backend logs |
| `trading-game logs backend` | `tg l b` | View backend logs |
| `trading-game logs frontend` | `tg l f` | View frontend logs |
| `trading-game open` | `tg o` | Open game in browser |
| `trading-game db-reset` | | Reset database (with confirmation) |

### Examples

```bash
# Restart servers
tg r

# Check status
tg status

# View logs
tg logs

# Open in browser
tg open

# Stop servers
tg stop
```

## What Gets Added to Your Terminal Header

After adding to your `.zshrc`, your terminal will show:

```
🚀 Python CLIs from workspace projects (3):
  - fireworks      - osm      - trading-game
```

You can run `trading-game` or `tg` from anywhere in your terminal!

## Manual Installation Steps

1. Open your `.zshrc` file:
   ```bash
   nano ~/.zshrc
   ```

2. Add at the end of the file:
   ```bash
   # Trading Game CLI
   source "/Users/mattmollart/Documents/personal vscode projects/TheTradingGame/trading-game-cli.sh"
   ```

3. Save and exit (Ctrl+X, then Y, then Enter in nano)

4. Reload your shell:
   ```bash
   source ~/.zshrc
   ```

5. Test it:
   ```bash
   tg
   ```

## Uninstall

To remove, simply delete or comment out the line in your `~/.zshrc`:
```bash
# source "/Users/mattmollart/Documents/personal vscode projects/TheTradingGame/trading-game-cli.sh"
```

Then reload:
```bash
source ~/.zshrc
```
