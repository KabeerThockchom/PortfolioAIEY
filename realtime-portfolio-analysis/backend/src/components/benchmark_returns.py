from sqlalchemy import func, extract, case
import pandas as pd
from src.components.filter_helper_functions import *
from src.database.database import SessionLocal
from src.components.helper_functions import process_time_period_data
from src.database.models import *
session = SessionLocal()

def get_index_returns(index_asset=['SPX'],interval='quarterly', time_history=2):
    
    # Get the list of index_id for some asset type
    asset_ids_query = select(AssetType.asset_id).where(AssetType.asset_ticker.in_(index_asset))
    asset_ids_result = session.execute(asset_ids_query).fetchall()

    # Extract the IDs from the result
    asset_ids = [int(id[0]) for id in asset_ids_result]

    filter_levels_dict = get_filter_levels_dict(session)
    dimension_levels = list(get_filters_dict(filter_levels_dict, index_asset).keys())

    valid_intervals = ['weekly', 'monthly', 'quarterly', 'yearly']
    if interval not in valid_intervals:
        raise ValueError(f"Invalid interval. Choose from {', '.join(valid_intervals)}")

    # Fetch all data for the given asset_ids
    query = select(AssetHistory.asset_id,
                    AssetHistory.close_price,
                    AssetHistory.date,
                    AssetType.asset_ticker.label('ticker')
                ).where(AssetHistory.asset_id.in_(asset_ids)).join(
                    AssetType, AssetHistory.asset_id == AssetType.asset_id
                ).order_by(AssetHistory.date)
    result = session.execute(query).fetchall()

    # Convert to DataFrame
    df = pd.DataFrame(result, columns=['asset_id', 'close_price', 'date', 'ticker'])

    df['date'] = pd.to_datetime(df['date'])

    df['year'] = df['date'].dt.year
    # Set date as index
    df.set_index('date', inplace=True)

    # Process each asset and combine results
    all_data = []
    for asset_id in asset_ids:
        asset_data = df[df['asset_id'] == asset_id]
        if not asset_data.empty:
            all_data.append(process_time_period_data(asset_data,dimension_levels,interval, time_history))

    all_data = pd.DataFrame(pd.concat(all_data, ignore_index=True))

    all_data = all_data.sort_values(['year', 'freq', 'index_name'], ascending=[False, False, True]).reset_index(drop=True)
    # Calculate returns for each index
    all_data['return'] = all_data.groupby('index_name')['close_price'].pct_change(-1) * 100
    all_data['return'] = round(all_data['return'],2)

    # Format close price
    all_data['close_price'] = round(all_data['close_price'],2)

    # Reorder columns
    columns = ['year', 'freq', 'last_date', 'index_name', 'close_price', 'return']
    all_data = all_data[columns]
    all_data = all_data.rename(columns={'index_name': 'dimension','close_price': 'portfolio','return': 'portfolio_return'})
    all_data = all_data.fillna(0)
    return all_data[:-1]