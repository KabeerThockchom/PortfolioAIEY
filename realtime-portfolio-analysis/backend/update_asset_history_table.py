import yfinance as yf  
import pandas as pd  
from datetime import datetime  
from dateutil.relativedelta import relativedelta  
from curl_cffi import requests  
from src.database.database import SessionLocal  
from src.database.models import AssetType, AssetHistory 
from src.pipeline.logger import logger 
  
def refresh_asset_history_table():  
    """  
    Update the AssetHistory table to ensure it contains only data for the latest 5 years.  
    Update existing records or insert new ones, and delete data older than 5 years.  
    """  
    session = SessionLocal()  
  
    # Create a session for yfinance  
    session_yf = requests.Session(impersonate="chrome")  
  
    # Get all non-cash assets from AssetType table  
    assets = session.query(AssetType).filter(AssetType.asset_ticker != "CASH").all()  
    if not assets:  
        print("No non-cash assets found in AssetType table.")  
        return  
  
    tickers = [asset.asset_ticker for asset in assets]  
    ticker_to_id = {asset.asset_ticker: asset.asset_id for asset in assets}  
  
    print(f"Found {len(tickers)} non-cash assets to refresh historical data for.")  
  
    # Define the time range for the latest 5 years  
    end_date = datetime.now()  
    start_date = end_date - relativedelta(years=5)  
  
    # Delete old data beyond the 5-year range  

    logger.bind(frontend=True).info(f"Deleting records older than {start_date.date()}")
    old_records_deleted = session.query(AssetHistory).filter(AssetHistory.date < start_date.date()).delete()  
    session.commit()  
    logger.bind(frontend=True).info(f"Deleted {old_records_deleted} old records from AssetHistory table.")  
  
    # Download historical data for all tickers  
    logger.bind(frontend=True).info(f"Downloading historical data for all tickers from {start_date.date()} to {end_date.date()}")  
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
  
    # Update historical data in the database  
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
            close_price = row['Close']  
  
            if float(close_price) != 0:  
                # Check if a record for the same asset_id and date already exists  
                existing_record = session.query(AssetHistory).filter_by(  
                    asset_id=asset_id, date=date_idx.date()  
                ).first()  
  
                if existing_record:  
                    # Update the existing record  
                    existing_record.close_price = float(close_price)  
                    session.add(existing_record)  
                else:  
                    # Insert a new record  
                    history_entry = AssetHistory(  
                        asset_id=asset_id,  
                        date=date_idx.date(),  
                        close_price=float(close_price)  # Ensure it's a float  
                    )  
                    session.add(history_entry)  
  
                records_count += 1  
                total_records += 1  
        
        print(f"Prepared {records_count} historical records for {ticker}")  
  
        # Commit in batches to avoid memory issues  
        if total_records % 1000 == 0:  
            session.commit()  
            logger.bind(frontend=True).info(f"Committed {total_records} records so far")
            print(f"Committed {total_records} records so far")  
  
    # Final commit for any remaining records  
    session.commit()  
    logger.bind(frontend=True).success(f"Successfully refreshed AssetHistory table with {total_records} new or updated records")
    print(f"Successfully refreshed AssetHistory table with {total_records} new or updated records")  
  
if __name__ == "__main__":  
    refresh_asset_history_table()  