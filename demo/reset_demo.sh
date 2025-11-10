#!/bin/bash
# reset_demo.sh
# Script to reset the demo database to its clean state

# Define paths
CLEAN_DB="/Users/kabeerthockchom/PortfolioAIEY/demo/voicebot_clean.sqlite3"
WORKING_DB="/Users/kabeerthockchom/PortfolioAIEY/realtime-portfolio-analysis/backend/src/database/voicebot.sqlite3"
BACKUP_DIR="/Users/kabeerthockchom/PortfolioAIEY/demo/backups"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Portfolio Demo Database Reset ===${NC}\n"

# Check if clean database exists
if [ ! -f "$CLEAN_DB" ]; then
    echo -e "${RED}ERROR: Clean database not found at $CLEAN_DB${NC}"
    echo "Please run generate_clean_db.py first to create the clean database"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create timestamped backup of current working database
if [ -f "$WORKING_DB" ]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/voicebot_backup_$TIMESTAMP.sqlite3"

    echo -e "${YELLOW}Backing up current database...${NC}"
    cp "$WORKING_DB" "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Backup created: $BACKUP_FILE${NC}\n"
    else
        echo -e "${RED}ERROR: Failed to create backup${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}No existing database found at $WORKING_DB${NC}\n"
fi

# Copy clean database to working location
echo -e "${YELLOW}Restoring clean database...${NC}"
cp "$CLEAN_DB" "$WORKING_DB"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database reset successfully!${NC}\n"

    # Display bank account balances
    echo -e "${GREEN}Clean database setup:${NC}"
    echo "  • Chase Bank (Checking): \$10,000"
    echo "  • Wells Fargo (Savings): \$20,000"
    echo "  • Bank of America (Money Market): \$30,000"
    echo -e "\n  ${GREEN}Total: \$60,000${NC}\n"

    echo -e "${YELLOW}Note: Restart your backend server for changes to take effect${NC}"
    exit 0
else
    echo -e "${RED}ERROR: Failed to copy clean database${NC}"
    exit 1
fi
