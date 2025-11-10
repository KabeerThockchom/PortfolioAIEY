# Real-time Portfolio Analysis with AI Voice Interface

An intelligent portfolio management system with real-time analysis and voice-controlled trading capabilities powered by Azure OpenAI and Pipecat.

## Features

### Core Functionality
- Real-time portfolio tracking and analysis
- Voice-controlled trading interface
- Multi-level portfolio composition analysis
- Risk assessment and attribution analysis
- Historical benchmarking and performance tracking
- Bank account integration for fund transfers

### Recent Enhancements (2025-11-09)

#### 1. Robust Price Fallback System
- **YahooFinance API with Database Fallback:** Automatically falls back to historical database prices if the YahooFinance API is unavailable
- **Logging and Transparency:** Clear warnings when using stale data, including price dates
- **Reliability:** Ensures portfolio calculations never fail due to API outages

#### 2. Voice-Enabled Bank Transfers by Name
- **Natural Language Support:** Transfer funds using bank names instead of numeric IDs
- **Fuzzy Matching:** Supports partial names and common abbreviations
  - "Chase" → Chase Bank
  - "Wells" → Wells Fargo
  - "BofA" / "BoA" → Bank of America
- **Smart Error Handling:** Helpful prompts when multiple or no matches found

#### 3. Demo Database Reset System
- **One-Command Reset:** Easily reset to clean demo state for presentations
- **Standardized Balances:** Clean database with $10k, $20k, $30k in bank accounts
- **Automatic Backups:** Timestamped backups created before each reset
- **Documentation:** Comprehensive README in `/demo/` folder

## Project Structure

```
PortfolioAIEY/
├── realtime-portfolio-analysis/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── controller.py          # Voice command handlers
│   │   │   │   ├── helper_functions.py    # Price fetching with fallback
│   │   │   │   ├── tool_schemas.py        # Voice tool schemas
│   │   │   │   └── yahoofinance.py        # YahooFinance API integration
│   │   │   └── database/
│   │   │       ├── models.py              # SQLAlchemy models
│   │   │       └── voicebot.sqlite3       # Working database
│   │   ├── create_data.py                 # Database initialization
│   │   └── update_asset_history_table.py  # Historical data updater
│   └── frontend/                          # React frontend
├── demo/
│   ├── voicebot_clean.sqlite3             # Clean demo database
│   ├── generate_clean_db.py               # Database generator script
│   ├── reset_demo.sh                      # Demo reset script
│   └── README.md                          # Demo documentation
├── CLAUDE.md                              # Development notes
└── README.md                              # This file
```

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- SQLite3
- Azure OpenAI API access (for voice features)

### Installation

1. **Clone the repository**
```bash
cd /Users/kabeerthockchom/PortfolioAIEY
```

2. **Backend Setup**
```bash
cd realtime-portfolio-analysis/backend
pip install -r requirements.txt
python create_data.py  # Initialize database
```

3. **Frontend Setup**
```bash
cd ../frontend
npm install
```

### Running the Application

**Start Backend:**
```bash
cd realtime-portfolio-analysis/backend
python main.py
```

**Start Frontend:**
```bash
cd realtime-portfolio-analysis/frontend
npm start
```

## Demo Reset (For Presentations)

Reset the database to a clean state with standardized bank balances:

```bash
cd /Users/kabeerthockchom/PortfolioAIEY/demo
./reset_demo.sh
```

This sets up:
- Chase Bank (Checking): $10,000
- Wells Fargo (Savings): $20,000
- Bank of America (Money Market): $30,000

See `/demo/README.md` for more details.

## Voice Commands

### Portfolio Queries
- "What's my portfolio worth?"
- "Show me my holdings"
- "What's my cash balance?"
- "How is my portfolio performing?"

### Trading Commands
- "Buy 10 shares of AAPL"
- "Sell 5 shares of Tesla"
- "Place a limit order for Microsoft at $350"

### Bank Transfers (New!)
- "Transfer $5000 from Chase"
- "Move $10000 from Wells Fargo to my brokerage"
- "Add $2000 from Bank of America"
- "Transfer $1000 from BofA" (abbreviated)

### Analysis Commands
- "Show me risk analysis by sector"
- "Compare my portfolio to benchmarks"
- "What's my asset allocation?"

## Database Schema

### Key Tables

**user_bank_accounts:**
- Bank account information for fund transfers
- Fields: bank_name, account_type, available_balance

**asset_history:**
- Historical price data for fallback
- Used when YahooFinance API is unavailable

**user_portfolio:**
- Current holdings and positions
- Real-time value calculations

**order_book:**
- Pending and completed orders
- Trade history tracking

## API Fallback Mechanism

The system uses a multi-tier price fetching strategy:

1. **Primary:** YahooFinance API (real-time)
2. **Secondary:** YahooFinance historical (1-day)
3. **Fallback:** Database asset_history (last known price)

When fallback is used, warnings are logged:
```
WARNING: Using stale database price for AAPL: $185.50 (from 2025-11-08)
```

## Development Notes

See `CLAUDE.md` for detailed technical documentation including:
- Implementation details for each enhancement
- Testing recommendations
- Future enhancement considerations
- Known limitations
- Maintenance notes

## Bank Name Fuzzy Matching

The system supports flexible bank name matching:

| User Input | Matched Bank |
|------------|--------------|
| "Chase" | Chase Bank |
| "Wells" | Wells Fargo |
| "Wells Fargo" | Wells Fargo |
| "BofA" | Bank of America |
| "BoA" | Bank of America |
| "Bank of America" | Bank of America |

See `backend/src/components/controller.py:3104-3110` for the full alias mapping.

## Configuration

### Database Location
Working: `/realtime-portfolio-analysis/backend/src/database/voicebot.sqlite3`
Clean Demo: `/demo/voicebot_clean.sqlite3`

### Environment Variables
(Add any necessary environment variables here)

## Troubleshooting

### Issue: Stock prices not updating
**Solution:** Check YahooFinance API connectivity. System will automatically use database fallback with a warning.

### Issue: Bank transfer says "account not found"
**Solution:** Use fuzzy names like "Chase", "Wells", or "BofA". Or run `get_bank_accounts_tool` to see available accounts.

### Issue: Demo database has wrong balances
**Solution:** Regenerate clean database:
```bash
cd demo
python3 generate_clean_db.py
```

## Testing

### Test Database Fallback
```python
# Simulate API failure
import helper_functions
price = helper_functions.get_realtime_stock_price('AAPL')
# Should log warning and return database price
```

### Test Voice Bank Transfer
Say: "Transfer $100 from Chase"
Expected: Successful transfer with confirmation message

### Test Demo Reset
```bash
cd demo && ./reset_demo.sh
```
Expected: Database reset with backups created

## Contributing

When making changes:
1. Update `CLAUDE.md` with technical details
2. Update this `README.md` with user-facing changes
3. Test with demo database reset
4. Verify voice commands still work

## License

(Add license information)

## Contact

(Add contact information)

## Acknowledgments

- Azure OpenAI for voice processing
- Pipecat for real-time audio streaming
- YahooFinance for market data
- SQLAlchemy for database ORM
