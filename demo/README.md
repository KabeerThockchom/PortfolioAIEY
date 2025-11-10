# Demo Database Reset

This folder contains a clean database file for resetting the demo to its initial state.

## Clean Database Setup

The `voicebot_clean.sqlite3` file contains:

### Bank Accounts (Total: $60,000)
- **Chase Bank** (Checking): $10,000
- **Wells Fargo** (Savings): $20,000
- **Bank of America** (Money Market): $30,000

### Sample Portfolio Holdings
- Standard user portfolio with common stocks
- Historical price data for realistic demonstrations

## How to Reset the Demo

### Option 1: Using the Reset Script (Recommended)
```bash
cd /Users/kabeerthockchom/PortfolioAIEY/demo
./reset_demo.sh
```

### Option 2: Manual Reset
```bash
cp /Users/kabeerthockchom/PortfolioAIEY/demo/voicebot_clean.sqlite3 \
   /Users/kabeerthockchom/PortfolioAIEY/realtime-portfolio-analysis/backend/src/database/voicebot.sqlite3
```

## Notes

- Always backup your current database before resetting if you need to preserve any data
- The reset script will create a timestamped backup automatically
- The clean database is read-only - the reset script creates a copy for actual use
