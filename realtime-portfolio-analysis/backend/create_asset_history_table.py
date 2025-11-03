import yfinance as yf
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from curl_cffi import requests

from src.database.database import SessionLocal
from src.database.models import AssetType, AssetHistory

def refresh_asset_history_table():
    """
    Delete all existing data in the AssetHistory table and insert fresh historical data
    up to the most recent common date available across all non-cash assets.
    """
    session = SessionLocal()
    
    # Create a session for yfinance
    session_yf = requests.Session(impersonate="chrome")
    
    # try:
    # Get all non-cash assets from AssetType table
    assets = session.query(AssetType).filter(AssetType.asset_ticker != "CASH").all()
    if not assets:
        print("No non-cash assets found in AssetType table.")
        return
    
    tickers = [asset.asset_ticker for asset in assets]
    ticker_to_id = {asset.asset_ticker: asset.asset_id for asset in assets}
    
    print(f"Found {len(tickers)} non-cash assets to refresh historical data for.")
    
    # Delete all existing records from AssetHistory table
    deleted_count = session.query(AssetHistory).delete()
    session.commit()
    print(f"Deleted {deleted_count} existing records from AssetHistory table.")
    
    # Set time range for historical data - last 5 years
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=5)
    
    # Download historical data for all tickers at once
    print(f"Downloading historical data for all tickers from {start_date.date()} to {end_date.date()}")
    historical_data = {}
    
    for ticker in tickers:
        try:
            if ticker == 'SPX':
                ticker = '^SPX'  # Use S&P 500 index ticker for SPX
            data = yf.download(ticker, start=start_date, end=end_date, session=session_yf)
            
            ticker = ticker.replace('^', '')  # Clean up ticker for consistency
            if not data.empty:
                historical_data[ticker] = data
                print(f"Successfully downloaded data for {ticker}: {len(data)} records")
            else:
                print(f"No data available for {ticker}")
        except Exception as e:
            print(f"Failed to download data for {ticker}: {str(e)}")
    
    if not historical_data:
        print("No historical data could be downloaded for any ticker.")
        return
    
    # Find the most recent common date across all tickers
    valid_tickers = list(historical_data.keys())
    common_dates = set(historical_data[valid_tickers[0]].index)
    for ticker in valid_tickers[1:]:
        ticker_dates = set(historical_data[ticker].index)
        common_dates.intersection_update(ticker_dates)
    
    if not common_dates:
        print("No common dates found across all tickers.")
        return
    
    most_recent_common_date = max(common_dates)
    print(f"Most recent common date across all tickers: {most_recent_common_date.date()}")
    
    # Insert historical data up to the most recent common date
    total_records = 0
    
    for ticker in valid_tickers:
        asset_id = ticker_to_id.get(ticker)
        if not asset_id:
            print(f"No asset_id found for ticker {ticker}, skipping.")
            continue
        
        # Filter data up to the most recent common date
        ticker_data = historical_data[ticker].loc[:most_recent_common_date]
        records_count = 0
        
        for date_idx, row in ticker_data.iterrows():
            # Use pd.isna correctly on a single value, not the entire Series
            close_price = row['Close']
            # print(float(close_price))
            if float(close_price) != 0:
                history_entry = AssetHistory(
                    asset_id=asset_id,
                    date=date_idx.date(),
                    close_price=float(close_price)  # Ensure it's a float
                )
                session.add(history_entry)
                records_count += 1
        
        total_records += records_count
        print(f"Prepared {records_count} historical records for {ticker}")
        
        # Commit in batches to avoid memory issues
        if total_records % 1000 == 0:
            session.commit()
            print(f"Committed {total_records} records so far")
    
    # Final commit for any remaining records
    session.commit()
    print(f"Successfully refreshed AssetHistory table with {total_records} new records")
        
    # except Exception as e:
    #     session.rollback()
    #     print(f"An error occurred during the asset history refresh: {e}")
    #     # Print the full traceback for better debugging
    #     import traceback
    #     traceback.print_exc()
    
    # finally:
    #     session.close()

def update_asset_history_table_with_new_values():
    """
    Update the AssetHistory table with the latest data.
    This function is a placeholder for future updates.
    """
    print("This function is a placeholder for future updates to the AssetHistory table.")
    # Implement update logic here if needed in the future


if __name__ == "__main__":
    refresh_asset_history_table()