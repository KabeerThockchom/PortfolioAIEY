# Portfolio Analysis Project - Development Notes

## Recent Enhancements (2025-11-09)

### 1. Demo Database Reset Infrastructure

**Location:** `/demo/`

Created a comprehensive demo reset system with the following components:

#### Files Created:
- `voicebot_clean.sqlite3` - Clean database with standardized bank balances
- `generate_clean_db.py` - Script to generate clean database from current working database
- `reset_demo.sh` - Bash script for one-command demo reset with automatic backup
- `README.md` - Documentation for demo reset procedures

#### Bank Account Setup (Clean Database):
- Chase Bank (Checking): $10,000
- Wells Fargo (Savings): $20,000
- Bank of America (Money Market): $30,000
- **Total:** $60,000

#### Usage:
```bash
# Generate a fresh clean database
cd /Users/kabeerthockchom/PortfolioAIEY/demo
python3 generate_clean_db.py

# Reset demo to clean state
./reset_demo.sh
```

The reset script automatically:
- Creates timestamped backups of current database
- Copies clean database to working location
- Displays summary of bank account balances
- Reminds to restart backend server

---

### 2. YahooFinance API Fallback to Database

**Location:** `backend/src/components/helper_functions.py`

#### Problem Solved:
When YahooFinance API fails or is unavailable, the application would return `None` for stock prices, breaking portfolio calculations.

#### Implementation:

Added `get_latest_db_price(symbol)` function that:
- Queries `asset_history` table for most recent `close_price`
- Returns price and date of last known price
- Used as fallback when API fails

Modified functions:
1. **`get_realtime_stock_price(symbol)`** (lines 162-217)
   - Now tries database fallback if API fails
   - Logs warning messages with price date when using stale data

2. **`get_realtime_prices_bulk(symbols)`** (lines 107-160)
   - Applies fallback for each symbol in batch
   - Logs each fallback occurrence for debugging

#### Logging Behavior:
```
WARNING: Using stale database price for AAPL: $185.50 (from 2025-11-08)
```

This ensures:
- Application never crashes due to API failures
- Users always see some price data, even if slightly stale
- Clear indication when database fallback is used

---

### 3. Voice-Enabled Bank Account Selection by Name

**Locations:**
- Schema: `backend/src/components/tool_schemas.py` (lines 505-529)
- Handler: `backend/src/components/controller.py` (lines 3063-3161)

#### Problem Solved:
Previously, users had to provide numeric `bank_account_id` to transfer funds, which wasn't natural for voice interactions.

#### Implementation:

**Schema Changes:**
- Made `bank_account_id` optional
- Added optional `bank_name` parameter
- Updated description to show users can say bank names
- Required fields: only `user_id` and `amount`

**Fuzzy Matching Logic:**
The system now supports:

1. **Exact Matches:**
   - "Chase Bank" → Chase Bank
   - "Wells Fargo" → Wells Fargo

2. **Partial Matches:**
   - "Chase" → Chase Bank
   - "Wells" → Wells Fargo
   - "Bank of America" → Bank of America

3. **Common Abbreviations:**
   - "BofA" → Bank of America
   - "BoA" → Bank of America
   - "WF" → Wells Fargo

4. **Case-Insensitive:**
   - "chase", "CHASE", "Chase" all work

**Error Handling:**
- **No matches:** Lists all available bank accounts
- **Multiple matches:** Asks user to be more specific
- **Exactly one match:** Proceeds with transfer

#### Example Voice Commands:
```
"Transfer $5000 from Chase"
"Move $10000 from Wells Fargo to my brokerage"
"Add $2000 from BofA"
```

**Code Location:** `backend/src/components/controller.py:3090-3150`

---

### 4. Technical Implementation Details

#### Database Schema (User Bank Accounts):
```sql
CREATE TABLE user_bank_accounts (
    bank_account_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    bank_name VARCHAR(100) NOT NULL,
    account_number VARCHAR(20) NOT NULL,  -- Masked: ***1234
    account_type VARCHAR(50) NOT NULL,     -- Checking, Savings, Money Market
    available_balance FLOAT NOT NULL DEFAULT 0.0,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
)
```

#### API Fallback Logic Flow:
```
1. Try YahooFinance API (primary)
   ↓ (fails)
2. Try ticker.history(period="1d")
   ↓ (fails)
3. Query asset_history table (fallback)
   ↓ (succeeds)
4. Return latest close_price with warning log
```

#### Bank Name Matching Algorithm:
```python
1. Normalize input: lowercase, strip whitespace
2. Check exact substring match
3. Check alias dictionary for common abbreviations
4. Return matches:
   - 0 matches: Show available banks
   - 1 match: Proceed with transfer
   - 2+ matches: Ask for clarification
```

---

### 5. Testing Recommendations

#### Test Case 1: Database Fallback
```bash
# Simulate API failure by disconnecting internet
# Expected: System should use database prices with warnings logged
```

#### Test Case 2: Voice Bank Transfer
Test these voice commands:
- "Transfer $100 from Chase"
- "Move $500 from Wells"
- "Add $1000 from Bank of America"
- "Transfer $200 from BofA"
- "Transfer $50 from XYZ Bank" (should show available banks)

#### Test Case 3: Demo Reset
```bash
cd /Users/kabeerthockchom/PortfolioAIEY/demo
./reset_demo.sh
# Verify bank balances: Chase=$10k, Wells=$20k, BofA=$30k
```

---

### 6. Files Modified

1. **`backend/src/components/helper_functions.py`**
   - Added `get_latest_db_price()` function
   - Modified `get_realtime_stock_price()`
   - Modified `get_realtime_prices_bulk()`

2. **`backend/src/components/tool_schemas.py`**
   - Updated `transfer_from_bank_tool` schema
   - Made `bank_account_id` optional
   - Added `bank_name` parameter

3. **`backend/src/components/controller.py`**
   - Enhanced `transfer_from_bank()` function
   - Added fuzzy matching for bank names
   - Improved error messages

4. **New Files Created:**
   - `/demo/voicebot_clean.sqlite3`
   - `/demo/generate_clean_db.py`
   - `/demo/reset_demo.sh`
   - `/demo/README.md`

---

### 7. Future Enhancements Considerations

1. **Cache database prices** in memory to reduce query overhead
2. **Add price staleness indicator** in UI when showing fallback prices
3. **Expand bank aliases** based on user feedback
4. **Add voice confirmation** for large transfers
5. **Implement scheduled database price updates** to keep fallback data fresh

---

### 8. Known Limitations

1. Database fallback prices may be stale (last update depends on `update_asset_history_table.py` schedule)
2. Fuzzy matching only supports pre-defined aliases (not ML-based)
3. Bank name matching is case-insensitive but doesn't handle typos
4. No partial amount suggestions if insufficient funds

---

## Maintenance Notes

- Clean database should be regenerated periodically to include latest portfolio data
- Asset history table should be updated regularly for accurate fallback prices
- Bank aliases in `controller.py` should be expanded based on user banks
- Demo reset script backups are stored in `/demo/backups/` (consider cleanup policy)
