"""
Seed script to create mock bank accounts for existing users.
Run this script to populate the user_bank_accounts table with sample data.
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import User, UserBankAccount, Base
from datetime import datetime

# Use absolute path for database
DATABASE_URL = "sqlite:///./src/database/voicebot.sqlite3"

def seed_bank_accounts():
    engine = create_engine(DATABASE_URL, echo=True)

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all users
        users = session.query(User).all()

        if not users:
            print("No users found in the database. Please create users first.")
            return

        print(f"Found {len(users)} users. Creating bank accounts...")

        # Mock bank account data for each user
        for user in users:
            # Check if user already has bank accounts
            existing_accounts = session.query(UserBankAccount).filter(
                UserBankAccount.user_id == user.user_id
            ).count()

            if existing_accounts > 0:
                print(f"User {user.username} (ID: {user.user_id}) already has {existing_accounts} bank account(s). Skipping...")
                continue

            # Create 3 mock bank accounts for each user
            bank_accounts = [
                UserBankAccount(
                    user_id=user.user_id,
                    bank_name="Chase Bank",
                    account_number="***1234",
                    account_type="Checking",
                    available_balance=15000.00,
                    is_active=1
                ),
                UserBankAccount(
                    user_id=user.user_id,
                    bank_name="Wells Fargo",
                    account_number="***5678",
                    account_type="Savings",
                    available_balance=25000.00,
                    is_active=1
                ),
                UserBankAccount(
                    user_id=user.user_id,
                    bank_name="Bank of America",
                    account_number="***9012",
                    account_type="Money Market",
                    available_balance=10000.00,
                    is_active=1
                )
            ]

            # Add accounts to session
            for account in bank_accounts:
                session.add(account)

            print(f"Created 3 bank accounts for user {user.username} (ID: {user.user_id})")

        # Commit the changes
        session.commit()
        print("\nBank accounts seeded successfully!")

        # Display summary
        total_accounts = session.query(UserBankAccount).count()
        print(f"\nTotal bank accounts in database: {total_accounts}")

    except Exception as e:
        session.rollback()
        print(f"Error seeding bank accounts: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("Starting bank account seeding process...")
    seed_bank_accounts()
    print("Done!")
