#!/usr/bin/env python3
"""
Script to generate a clean demo database with specified bank account balances.
This creates a fresh database copy with:
- Chase Bank (Checking): $10,000
- Wells Fargo (Savings): $20,000
- Bank of America (Money Market): $30,000
"""

import shutil
import sqlite3
from datetime import datetime
import os

# Paths
SOURCE_DB = "/Users/kabeerthockchom/PortfolioAIEY/realtime-portfolio-analysis/backend/src/database/voicebot.sqlite3"
CLEAN_DB = "/Users/kabeerthockchom/PortfolioAIEY/demo/voicebot_clean.sqlite3"

def create_clean_database():
    """Create a clean demo database with specified bank account balances."""

    # Check if source database exists
    if not os.path.exists(SOURCE_DB):
        print(f"ERROR: Source database not found at {SOURCE_DB}")
        return False

    print(f"Creating clean database from {SOURCE_DB}...")

    # Create a backup of existing clean database if it exists
    if os.path.exists(CLEAN_DB):
        backup_path = f"{CLEAN_DB}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(CLEAN_DB, backup_path)
        print(f"Backed up existing clean database to {backup_path}")

    # Copy the source database to create clean version
    shutil.copy2(SOURCE_DB, CLEAN_DB)
    print(f"Copied database to {CLEAN_DB}")

    # Connect to the clean database and update bank account balances
    conn = sqlite3.connect(CLEAN_DB)
    cursor = conn.cursor()

    try:
        # Check if user_bank_accounts table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='user_bank_accounts'
        """)

        if not cursor.fetchone():
            print("WARNING: user_bank_accounts table does not exist in database")
            print("Creating user_bank_accounts table...")

            cursor.execute("""
                CREATE TABLE user_bank_accounts (
                    bank_account_id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    bank_name VARCHAR(100) NOT NULL,
                    account_number VARCHAR(20) NOT NULL,
                    account_type VARCHAR(50) NOT NULL,
                    available_balance FLOAT NOT NULL DEFAULT 0.0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            print("Created user_bank_accounts table")

        # Clear existing bank accounts
        cursor.execute("DELETE FROM user_bank_accounts")
        print("Cleared existing bank accounts")

        # Insert the three bank accounts with specified balances
        bank_accounts = [
            (1, 1, "Chase Bank", "***1234", "Checking", 10000.0, 1),
            (2, 1, "Wells Fargo", "***5678", "Savings", 20000.0, 1),
            (3, 1, "Bank of America", "***9012", "Money Market", 30000.0, 1)
        ]

        cursor.executemany("""
            INSERT INTO user_bank_accounts
            (bank_account_id, user_id, bank_name, account_number, account_type, available_balance, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, bank_accounts)

        print("\nInserted bank accounts:")
        for acc in bank_accounts:
            print(f"  - {acc[2]} ({acc[4]}): ${acc[5]:,.2f} (Account: {acc[3]})")

        # Verify the data
        cursor.execute("""
            SELECT bank_name, account_type, available_balance
            FROM user_bank_accounts
            ORDER BY bank_account_id
        """)

        results = cursor.fetchall()
        total_balance = sum(row[2] for row in results)

        print(f"\nTotal bank balances: ${total_balance:,.2f}")

        # Commit the changes
        conn.commit()
        print("\nClean database created successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"ERROR: Failed to create clean database: {e}")
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    success = create_clean_database()
    if success:
        print(f"\nClean database is ready at: {CLEAN_DB}")
        print("Use reset_demo.sh to copy this to the working database location")
    else:
        print("\nFailed to create clean database")
