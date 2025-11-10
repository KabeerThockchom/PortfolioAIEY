import json
import random
import pandas as pd
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from src.database.database import SessionLocal
from src.database.models import *

class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

def calculate_available_cash_balance(user_id, db_session):
    """
    Centralized function to calculate available cash balance for a user.
    This function ensures consistency across all API endpoints and tools.

    IMPORTANT: ALL code that needs to display or check cash balance MUST use this function.
    Do NOT query UserPortfolio.investment_amount for CASH directly, as it does not account
    for pending "Under Review" buy orders.

    Formula: Available Cash = Total CASH in UserPortfolio - Sum of "Under Review" Buy Orders

    Args:
        user_id: The user's ID
        db_session: SQLAlchemy database session

    Returns:
        float: Available cash balance (total cash - pending buy orders), rounded to 2 decimals

    Raises:
        Exception: If cash asset not found or other database errors

    Used in:
        - GET /api/cash_balance (header display)
        - get_portfolio_summary (portfolio table CASH row)
        - place_trade, update_trade, confirm_trade (order summary)
        - transfer_from_bank, get_bank_accounts (fund transfer tools)
    """
    from sqlalchemy import func

    # Get the cash asset ID
    cash_asset_id = db_session.query(AssetType.asset_id).filter(
        AssetType.asset_ticker == 'CASH'
    ).scalar()

    if not cash_asset_id:
        raise Exception("Cash asset not found in database")

    # Get the total cash balance from user's portfolio
    cash_balance = db_session.query(UserPortfolio.investment_amount).filter(
        UserPortfolio.user_id == user_id,
        UserPortfolio.asset_id == cash_asset_id
    ).scalar() or 0.0

    # Get the total value of buy orders that are under review (pending confirmation)
    # Note: "Placed" orders are already executed and reflected in the cash_balance
    total_pending_buy_value = db_session.query(func.sum(OrderBook.amount)).filter(
        OrderBook.user_id == user_id,
        OrderBook.buy_sell == 'Buy',
        OrderBook.order_status == 'Under Review'
    ).scalar() or 0.0

    # Available cash = total cash - pending buy orders
    available_cash = cash_balance - total_pending_buy_value

    return round(available_cash, 2)

def get_latest_db_price(symbol):
    """
    Fetch the latest price for a symbol from the asset_history table.
    This is used as a fallback when the YahooFinance API fails.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')

    Returns:
        tuple: (price, date) - Latest price and its date, or (None, None) if not found
    """
    db = SessionLocal()
    try:
        # Get the asset ID for the symbol
        asset = db.query(AssetType).filter(AssetType.asset_ticker == symbol).first()

        if not asset:
            return None, None

        # Get the most recent price from asset_history
        latest_history = db.query(AssetHistory).filter(
            AssetHistory.asset_id == asset.asset_id
        ).order_by(AssetHistory.date.desc()).first()

        if latest_history:
            return round(float(latest_history.close_price), 2), latest_history.date

        return None, None
    except Exception as e:
        print(f"Error fetching database price for {symbol}: {e}")
        return None, None
    finally:
        db.close()

def get_realtime_prices_bulk(symbols):
    """
    Fetch real-time prices for multiple symbols using yfinance.
    Falls back to database prices if API fails.

    Args:
        symbols: List of ticker symbols

    Returns:
        dict: Mapping of symbol to current price {symbol: price}
    """
    import yfinance as yf
    from curl_cffi import requests

    prices = {}
    session = requests.Session(impersonate="chrome")

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol, session=session)
            info = ticker.info

            # Try multiple price sources
            current_price = None
            if 'currentPrice' in info and info['currentPrice']:
                current_price = info['currentPrice']
            elif 'regularMarketPrice' in info and info['regularMarketPrice']:
                current_price = info['regularMarketPrice']
            elif 'previousClose' in info and info['previousClose']:
                current_price = info['previousClose']

            if current_price is None:
                # Fallback to history
                hist = ticker.history(period="1d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]

            if current_price:
                prices[symbol] = round(float(current_price), 2)
            else:
                # API failed, try database fallback
                db_price, price_date = get_latest_db_price(symbol)
                if db_price is not None:
                    prices[symbol] = db_price
                    print(f"WARNING: Using stale database price for {symbol}: ${db_price} (from {price_date})")
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            # Try database fallback
            db_price, price_date = get_latest_db_price(symbol)
            if db_price is not None:
                prices[symbol] = db_price
                print(f"WARNING: Using stale database price for {symbol}: ${db_price} (from {price_date})")

    return prices

def get_realtime_stock_price(symbol):
    """
    Fetch real-time price for a single stock symbol using yfinance.
    Falls back to database prices if API fails.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')

    Returns:
        float: Current stock price, or None if unable to fetch

    Example:
        price = get_realtime_stock_price('AAPL')
        # Returns: 211.14
    """
    import yfinance as yf
    from curl_cffi import requests

    try:
        session = requests.Session(impersonate="chrome")
        ticker = yf.Ticker(symbol, session=session)
        info = ticker.info

        # Try multiple price sources
        current_price = None
        if 'currentPrice' in info and info['currentPrice']:
            current_price = info['currentPrice']
        elif 'regularMarketPrice' in info and info['regularMarketPrice']:
            current_price = info['regularMarketPrice']
        elif 'previousClose' in info and info['previousClose']:
            current_price = info['previousClose']

        if current_price is None:
            # Fallback to history
            hist = ticker.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]

        if current_price:
            return round(float(current_price), 2)
        else:
            # API failed, try database fallback
            print(f"Warning: Could not fetch live price for {symbol}, trying database fallback...")
            db_price, price_date = get_latest_db_price(symbol)
            if db_price is not None:
                print(f"WARNING: Using stale database price for {symbol}: ${db_price} (from {price_date})")
                return db_price
            return None
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        # Try database fallback
        db_price, price_date = get_latest_db_price(symbol)
        if db_price is not None:
            print(f"WARNING: Using stale database price for {symbol}: ${db_price} (from {price_date})")
            return db_price
        return None

def ticker_to_asset_name_mapping():
    """
    Create a mapping of asset tickers to asset names.
    This is used to standardize the asset names in the aggregation tool.
    """
    db = SessionLocal()
    try:
        asset_types = db.query(AssetType.asset_ticker, AssetType.asset_name).all()
        mapping = {asset_ticker: asset_name for asset_ticker, asset_name in asset_types}
        return mapping
    finally:
        db.close()

def format_dimension(dimension):
    if dimension in ['asset_class', 'asset_ticker','asset_name','asset_manager']:
        return ' '.join(word.capitalize() for word in dimension.split('_'))
    else:
        return dimension.capitalize()
    
def process_time_period_data(asset_data, dimension_levels, interval, time_history):
    asset_data = asset_data.copy()
    
    # Add a column for the last available date
    asset_data['last_available_date'] = asset_data.index

    # Get the last date in the data
    last_date = asset_data.index.max()
    interval_str = interval
    # Define the interval based on interval
    if interval == 'weekly':
        interval = relativedelta(weeks=1)
    elif interval == 'monthly':
        interval = relativedelta(months=1)
    elif interval == 'quarterly':
        interval = relativedelta(months=3)
    else:  # yearly
        interval = relativedelta(years=1)

    # Calculate the start date based on time_history, adding one extra interval
    start_date = last_date - relativedelta(years=time_history) - interval

    # Create a list of target dates for resampling
    target_dates = []
    current_date = last_date
    while current_date >= start_date:
        target_dates.append(current_date)
        current_date -= interval

    # Resample the data
    result = pd.DataFrame()
    for i in range(len(target_dates) - 1):
        end_target = target_dates[i]
        start_target = target_dates[i + 1]

        # Find the actual end date (latest available date not exceeding the target)
        end_actual = asset_data[asset_data.index <= end_target].index.max()
        if pd.isnull(end_actual):
            continue  # Skip this period if no data is available

        # Find the actual start date (latest available date not exceeding the target)
        start_actual = asset_data[(asset_data.index <= start_target) & (asset_data.index < end_actual)].index.max()
        if pd.isnull(start_actual):
            start_actual = asset_data.index.min()  # Use the earliest date if no earlier data is available

        period_data = asset_data[(asset_data.index > start_actual) & (asset_data.index <= end_actual)]
        
        if not period_data.empty:
            period_result = pd.DataFrame({
                'aligned_date': [end_target],  # Keep the target date for alignment
                'actual_date': [end_actual],   # Add the actual date used
                'year': [end_target.year],     # Use end_target.year
                'index_name': [period_data[dimension_levels[0]].iloc[-1]] if 'all' not in dimension_levels else "portfolio",
                'open_price': [period_data['close_price'].iloc[0]],
                'high_price': [period_data['close_price'].max()],
                'low_price': [period_data['close_price'].min()],
                'close_price': [period_data['close_price'].iloc[-1]],
                'average_price': [period_data['close_price'].mean()],
                'number_of_records': [len(period_data)],
                'last_date': [period_data.index[-1]]
            })
            result = pd.concat([result, period_result], ignore_index=True)

    # Add interval column with correct formatting
    if interval_str == 'weekly':
        result['freq'] = result['actual_date'].dt.strftime('%Y-W%W')
    elif interval_str == 'monthly':
        result['freq'] = result['actual_date'].dt.strftime('%Y-%m')
    elif interval_str == 'quarterly':
        result['freq'] = result['actual_date'].dt.to_period('Q').astype(str)
    else:  # yearly
        result['freq'] = result['actual_date'].dt.strftime('%Y')
    return result

def transform_to_donut_chart_format_single_level(data, label_field=None, value_field='percentage', chart_type='donut',
                                  title="Donut Chart", description="Data distribution"):

    """
    Transform single-level data into a specific donut chart format.
   
    Args:
        data: List of dictionaries containing the data
        label_field: The field to use as labels (if None, auto-detects)
        value_field: The field to use as values (defaults to 'percentage')
        title: Chart title
        description: Chart description
   
    Returns:
        Dictionary formatted for donut chart as specified
    """
    if not data:
        return {
            "chartType": chart_type,
            "title": title,
            "description": description,
            "data": {
                "labels": [],
                "datasets": {
                    "data": [],
                    "backgroundColor": []
                }
            }
        }
   
    # Auto-detect label field if not provided
    if label_field is None:
        # Use first field that isn't the value field and isn't numeric
        sample = data[0]
        for field in sample.keys():
            if field != value_field and not isinstance(sample[field], (int, float)):
                label_field = field
                break
       
        if label_field is None:
            # Fallback to first field that isn't value field
            label_field = next(f for f in sample.keys() if f != value_field)
   
    # Filter out items with zero values
    filtered_data = [item for item in data if item.get(value_field, 0) > 0]
   
    # Extract labels and data values
    labels = [item[label_field] for item in filtered_data]
    values = [item[value_field] for item in filtered_data]
   
    # Generate some random colors for each segment
    colors = []
    for _ in range(len(labels)):
        color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        colors.append(color)
   
    # Create the output structure
    result = {
        "chartType": chart_type,
        "title": title,
        "description": description,
        "data": {
            "labels": labels,
            "datasets": {
                "data": values,
                "backgroundColor": colors
            }
        }
    }

    # with open('donut_chart.json', 'w') as f:
    #     json.dump(result, f, indent=2, cls=DateEncoder)
    return result

def transform_to_donut_chart_format_double_level(data, 
                                               outer_field='asset_class', 
                                               inner_field='sector',
                                               value_field='percentage',
                                               chart_type='donut',
                                               title="Multi-Level Donut Chart", 
                                               description="Asset class and sector distribution"):
    """
    Transform two-level data into a nested donut chart format with outer and inner rings.
    
    Args:
        data: List of dictionaries containing the data
        outer_field: The field to use for the outer ring (e.g., 'asset_class')
        inner_field: The field to use for the inner ring (e.g., 'sector')
        value_field: The field to use as values (defaults to 'percentage')
        title: Chart title
        description: Chart description
    
    Returns:
        Dictionary formatted for a multi-level donut chart with the specified format
    """
    if not data:
        return {
            "chartType": chart_type,
            "title": title,
            "description": description,
            "data": {
                "labels": [],
                "labels_ids": [],
                "datasets": {
                    "data": [],
                    "backgroundColor": [],
                    "hoverBackgroundColor": []
                },
                "subsets": {}
            }
        }
    
    # Group data by outer field (e.g., asset_class)
    outer_groups = defaultdict(list)
    for item in data:
        outer_groups[item[outer_field]].append(item)
    
    # Prepare outer ring data
    outer_labels = []
    outer_labels_ids = []
    outer_values = []
    outer_colors = []
    
    # Prepare subsets for inner rings
    subsets = {}
    
    for outer_category, items in outer_groups.items():
        # Generate ID for this category (lowercase with underscores)
        category_id = outer_category.lower().replace(' ', '_').replace('-', '_')
        
        # Sum values for the outer category
        outer_total = round(sum(item[value_field] for item in items),2)
        
        # Skip if the total is zero
        if outer_total <= 0:
            continue
            
        # Generate a color for this category
        category_color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        
        # Add to outer ring
        outer_labels.append(outer_category)
        outer_labels_ids.append(category_id)
        outer_values.append(outer_total)
        outer_colors.append(category_color)
        
        # Process inner segments for this category
        inner_segments = defaultdict(float)
        for item in items:
            inner_segments[item[inner_field]] += item[value_field]
        
        # Prepare inner segment data
        inner_labels = []
        inner_values = []
        inner_colors = []
        
        # Process each inner segment
        for inner_segment, segment_value in sorted(inner_segments.items()):
            if segment_value <= 0:
                continue
                
            inner_labels.append(inner_segment)
            inner_values.append(round(segment_value,2))
            
            # Generate a related color for this segment (a shade of the outer color)
            base_r = int(category_color[1:3], 16)
            base_g = int(category_color[3:5], 16)
            base_b = int(category_color[5:7], 16)
            
            # Get a varied shade for this segment
            shade_factor = 0.7 + (len(inner_colors) * 0.1) % 0.3  # Varies between 0.7 and 1.0
            inner_color = "#{:02x}{:02x}{:02x}".format(
                min(255, int(base_r * shade_factor)),
                min(255, int(base_g * shade_factor)),
                min(255, int(base_b * shade_factor))
            )
            inner_colors.append(inner_color)
        
        # Add this category's inner segments to subsets
        if inner_labels:
            subsets[category_id] = {
                "labels": inner_labels,
                "data": inner_values,
                "backgroundColor": inner_colors
            }
    
    # Create the output structure in the specified format
    result = {
        "chartType": chart_type,
        "title": title,
        "description": description,
        "data": {
            "labels": outer_labels,
            "labels_ids": outer_labels_ids,
            "datasets": {
                "data": outer_values,
                "backgroundColor": outer_colors,
                "hoverBackgroundColor": outer_colors.copy()  # Same colors for hover
            },
            "subsets": subsets
        }
    }
    # with open('donut_chart2.json', 'w') as f:
    #     json.dump(result, f, indent=2, cls=DateEncoder)
    return result
    
    return result


def transform_to_stack_bar_chart_format(data, 
                                       title="Quarterly Sector Performance", 
                                       description="Portfolio returns by sector across quarters",
                                       value_field="portfolio_return",
                                       color_palette=None):
    """
    Transform sector performance data into stack-bar chart format.
    
    Args:
        data: List of dictionaries containing sector performance data
        title: Chart title
        description: Chart description
        value_field: The field to use as values (defaults to 'portfolio_return')
        color_palette: Optional list of colors for sectors
        
    Returns:
        Dictionary formatted for stack-bar chart visualization with all available quarters
    """
    if not data:
        return {
            "chartType": "stack-bar",
            "title": title,
            "description": description,
            "data": {
                "labels": [],
                "datasets": []
            },
            "statistics": {}
        }
    
    # Define color palette if not provided
    if color_palette is None:
        color_palette = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", 
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
            "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5"
        ]
    
    # Extract unique sectors
    sectors = sorted(set(item["sector"] for item in data))
    
    # Sort data chronologically by year and quarter
    # First, create a helper function to convert quarter to a sortable value
    def quarter_sort_key(item):
        year = item["year"]
        # Extract quarter number from quarter string (e.g., "2023Q3" -> 3)
        quarter = int(item["quarter"].split("Q")[1])
        # Create a sortable key (e.g., 2023.3)
        return year + (quarter - 1) / 10.0
    
    # Sort data by date
    sorted_data = sorted(data, key=quarter_sort_key)
    
    # Get unique quarters, sorted chronologically
    quarters = []
    seen = set()
    for item in sorted_data:
        quarter = item["quarter"]
        if quarter not in seen:
            quarters.append(quarter)
            seen.add(quarter)
    
    # Organize data by sector and quarter
    sector_quarter_values = defaultdict(dict)
    for item in data:
        sector = item["sector"]
        quarter = item["quarter"]
        sector_quarter_values[sector][quarter] = item[value_field]
    
    # Prepare datasets (one per sector)
    datasets = []
    for i, sector in enumerate(sectors):
        color_idx = i % len(color_palette)
        
        # Get values for this sector across all quarters
        values = []
        for quarter in quarters:
            values.append(sector_quarter_values[sector].get(quarter, 0))
        
        datasets.append({
            "label": sector,
            "data": values,
            "borderColor": color_palette[color_idx],
            "backgroundColor": color_palette[color_idx],
            "fill": True,
        })
    
    # Calculate statistics
    all_returns = [item[value_field] for item in data]
    valid_returns = [r for r in all_returns if r is not None]
    
    statistics = {}
    if valid_returns:
        # Latest quarter statistics
        latest_quarter = quarters[-1]
        latest_returns = [item[value_field] for item in data if item["quarter"] == latest_quarter]
        
        # Find highest and lowest returns
        highest_return = max(valid_returns) if valid_returns else 0
        lowest_return = min(valid_returns) if valid_returns else 0
        avg_return = sum(valid_returns) / len(valid_returns) if valid_returns else 0
        
        # Format statistics
        statistics = {
            f"Latest Quarter ({latest_quarter})": f"{sum(latest_returns)/len(latest_returns):.2f}%" if latest_returns else "N/A",
            "Highest Quarterly Return": f"{highest_return:.2f}%",
            "Lowest Quarterly Return": f"{lowest_return:.2f}%",
            "Average Return": f"{avg_return:.2f}%"
        }
        
        # Add top performing sector
        sector_avg_returns = {}
        for sector in sectors:
            sector_data = [item[value_field] for item in data if item["sector"] == sector]
            if sector_data:
                sector_avg_returns[sector] = sum(sector_data) / len(sector_data)
        
        if sector_avg_returns:
            top_sector = max(sector_avg_returns.items(), key=lambda x: x[1])
            worst_sector = min(sector_avg_returns.items(), key=lambda x: x[1])
            
            statistics["Top Performing Sector"] = f"{top_sector[0]} ({top_sector[1]:.2f}%)"
            statistics["Worst Performing Sector"] = f"{worst_sector[0]} ({worst_sector[1]:.2f}%)"
    
    # Create the output structure
    result = {
        "chartType": "stack-bar",
        "title": title,
        "description": description,
        "data": {
            "labels": quarters,
            "datasets": datasets
        },
        "statistics": statistics
    }
    
    return result

def performance_chart(df_bar, df_line,time_period,interval,title="Historical Benchmarking",y_axis_display_name="Indexed Value (start=100)"):
    
    json_structure = {
        "type": "json",
        "type_of_data": "chart",
        "query_type": "portfolio_benchmark",
        "data": {
            "type_of_chart": "line_bar",
            "x_axis": "date",
            "y_line_axis": "value",
            "y_bar_axis": "return",
            "x_axis_display_name": "Date",
            "y_axis_bar_display_name": "Returns (%)",
            "y_axis_line_display_name": y_axis_display_name,
            "title": title,
            "interval": interval,
            "range" : f"{time_period}yr",
            "bar_chart_data": [],
            "line_chart_data": []
        }
    }

    # Generate bar chart data
    for _, row in df_bar.iterrows():
        bar_data = {
            "dimension": row.get('dimension', row.get('portfolio', '')),
            # "quarter": row['quarter'],
            "quarter" : row['last_date'],
            "date": row['last_date'],
            "year": row['year'],
            "return": row['portfolio_return']
        }
        json_structure["data"]["bar_chart_data"].append(bar_data)

    # Generate line chart data
    for d, group in df_line.groupby('dimension'):
        line_data = {
            "display_name": d,
            "rows": []
        }
        for _, row in group.iterrows():
            line_data["rows"].append({
                "date": row['date'],
                "value": row['portfolio_return']
            })
        json_structure["data"]["line_chart_data"].append(line_data)

    #save the json_structure to a file
    with open('performance_chart.json', 'w') as f:
        json.dump(json_structure, f, indent=2, cls=DateEncoder)
    return json.dumps(json_structure,cls=DateEncoder)


def aggregation_json(df,dimension,filters=None):
    # Create the base structure of the JSON
    json_structure = {
        "type": "json",
        "type_of_data": "chart",
        "query_type": "aggregation",
        "data": {
            "type_of_chart": "donut",
            "filters": filters,
            "group_by": dimension,
            "title": "Portfolio Composition",
            "rows": []
        }
    }

    # Define the possible columns
    possible_columns = ['asset_class', 'sector', 'category','legal_type']

    if filters==None:
        # Populate the rows
        for _, row in df.iterrows():
            row_data = {}
            for i in dimension:
                row_data[i] = row[i]

            row_data['value'] = row['weighted_value']
            row_data['percentage'] = row['percentage_value']

            json_structure["data"]["rows"].append(row_data)
    else:

        # Populate the rows
        for _, row in df.iterrows():
            row_data = {}
            for col in possible_columns:
                if col in df.columns:
                    row_data[col] = row[col]
            
            row_data['value'] = row['weighted_value']
            row_data['percentage'] = row['percentage_value']
            
            json_structure["data"]["rows"].append(row_data)
           

    # Convert to JSON string
    json_output = json.dumps(json_structure, indent=4)

    # Optionally, save to a file
    # with open('portfolio_composition.json', 'w') as f:
    #     f.write(json_output)

def format_relative_performance_chart(results,range,title):
    """
    Convert relative performance results into the required chart JSON format.
    
    Args:
        results: List of dictionaries with holding info, benchmark info, and comparative returns
    
    Returns:
        JSON object formatted for chart visualization
    """
    # Extract all holding tickers for x_axis_data
    x_axis_data = [item["holding_ticker"] for item in results]

    ticker_to_asset_name=ticker_to_asset_name_mapping()
    x_axis_data = [ticker_to_asset_name.get(ticker, ticker) for ticker in x_axis_data]
    
    # Create stack bar data for holdings and benchmarks
    holding_data = [item["holding_return"] for item in results]
    holding_data_names = [item["holding_ticker"] for item in results]
    
    benchmark_data = [item["benchmark_return"] for item in results]
    benchmark_data_names = [item["benchmark_ticker"] for item in results]
    
    stack_bar_data = [
        {
            "name": "Holdings",
            "data": holding_data,
            "data_name": holding_data_names
        },
        {
            "name": "Benchmark",
            "data": benchmark_data,
            "data_name": benchmark_data_names
        }
    ]
    
    # Create the final chart data structure
    chart_data = {
        "type": "json",
        "type_of_data": "chart",
        "query_type": "relative_performance",
        "data": {
            "type_of_chart": "bar",
            "x_axis": "holdings",
            "y_axis": "return",
            "x_axis_display_name": "Holdings",
            "y_axis_display_name": "Returns (%)",
            "title": title,
            "range": range,
            "x_axis_data": x_axis_data,
            "stack_bar_data": stack_bar_data
        }
    }
    
    return chart_data

# def generate_risk_analysis_visualization_json(simplified_data):
#     """
#     Generate a complete JSON structure for frontend visualization of portfolio risk data.
    
#     Args:
#         db: SQLAlchemy database session
#         user_id: ID of the user whose portfolio to analyze
        
#     Returns:
#         JSON string formatted for frontend visualization components
#     """
#     # Get simplified portfolio data
    
#     # Extract unique asset classes and calculate average risk scores for gauge chart
#     asset_classes = {}
#     for item in simplified_data:
#         asset_class = item["Asset Class"]
#         risk_score = item["Risk Score"]
        
#         if asset_class not in asset_classes:
#             asset_classes[asset_class] = {"total_risk": risk_score, "count": 1, "holdings_value": item["Holding Value"]}
#         else:
#             asset_classes[asset_class]["total_risk"] += risk_score
#             asset_classes[asset_class]["count"] += 1
#             asset_classes[asset_class]["holdings_value"] += item["Holding Value"]
    
#     # Calculate average risk score for each asset class
#     gauge_data = []
#     for asset_class, info in asset_classes.items():
#         avg_risk = info["total_risk"] / info["count"]
#         gauge_data.append({
#             "asset_class": asset_class,
#             "risk_score": avg_risk,
#             "total_value": info["holdings_value"]
#         })
    
#     # Prepare bubble chart data using the requested format
#     bubble_data = []
#     for item in simplified_data:
#         bubble_data.append({
#             "asset_class": item["Asset Class"]+"-"+item["Asset Class"],
#             "holding": item["Holding"],
#             "value": item["Holding Value"],
#             "risk_score": item["Risk Score"]
#         })
    
#     # Create the final JSON structure
#     visualization_data = {
#         "type": "json",
#         "type_of_data": "chart",
#         "query_type": "risk_analysis",
#         "data": {
#             "bubble_chart": {
#                 "title": "Portfolio Holdings Risk Analysis",
#                 "description": "Bubble size indicates risk level, position indicates asset class and value",
#                 "x_axis": "asset_class",
#                 "bubble_label": "holding",
#                 "y_axis": "value",
#                 "size": "risk_score",
#                 "items": bubble_data
#             },
#             "gauge_chart": {
#                 "title": "Asset Class Risk Levels",
#                 "description": "Average risk level by asset class",
#                 "category": "asset_class",
#                 "value": "risk_score",
#                 "size": "total_value",
#                 "min": 1,
#                 "max": 5,
#                 "items": gauge_data
#             }
#         }
#     }
    
#     return visualization_data

def generate_risk_analysis_visualization_json(holdings_data, weighted_risk_score,dimension_level="asset_class"):
    # Group holdings by asset class for processing
    # asset_classes = set(holding["Asset Class Concentration"] for holding in holdings_data)

    #sort the holdings_data by risk score
    holdings_data.sort(key=lambda x: x["holding_value"])
    print("Holdings Data",holdings_data)
    
    def dimension_level_to_key(dimension_level):
        if dimension_level == "ticker":
            return "ticker"
        elif dimension_level == "asset_class":
            return "asset_class"
        elif dimension_level == "concentration":
            return "concentration"
        elif dimension_level == "asset_manager":
            return "asset_manager"
        else:
            raise ValueError(f"Invalid dimension level: {dimension_level}")
    
    risk_score_ranges = {
        "<=2.0": lambda score: score <= 2.0,
        "2.01 - 3.0": lambda score: 2.0 < score <= 3.0,
        "3.01 - 4.0": lambda score: 3.0 < score <= 4.0,
        "4.01 - 5.0": lambda score: 4.0 < score <= 5.0,
        "5.01 - 6.0": lambda score: 5.0 < score <= 6.0,
        "6.01 - 8.0": lambda score: 6.0 < score <= 8.0,
        ">8.0": lambda score: score > 8.0
    }

    # Group data by risk range for bubble chart
    holdings_by_risk_range = {}

    for holding in holdings_data:
        risk_score = holding["risk_score"]
        risk_range = next((range_name for range_name, range_func in risk_score_ranges.items() if range_func(risk_score)), "Unknown")
        
        if risk_range not in holdings_by_risk_range:
            holdings_by_risk_range[risk_range] = {
                "name": risk_range,
                "data": []
            }
           

    # Get unique dimension values based on the dimension_level
    if dimension_level == "ticker":
        unique_values = set(holding["ticker"] for holding in holdings_data)
    elif dimension_level == "asset_class":
        unique_values = set(holding["asset_class"] for holding in holdings_data)
    elif dimension_level == "concentration":
        unique_values = set(holding["concentration"] for holding in holdings_data)
    elif dimension_level == "asset_manager":
        unique_values = set(holding["asset_manager"] for holding in holdings_data)
    else:
        raise ValueError(f"Invalid dimension level: {dimension_level}")

    # Create data points for each unique value across all risk ranges
    for risk_range, holding_data in holdings_by_risk_range.items():
        # Add initial empty data point
        holding_data["data"].append({
            "x": "",
            "y": 0,
            "z": ""
        })

        for value in unique_values:
            # Find matching holdings for this value and risk range
            matching_holdings = [h for h in holdings_data 
                                 if h[dimension_level_to_key(dimension_level)] == value 
                                 and risk_score_ranges[risk_range](h["risk_score"])]
            
            if matching_holdings:
                # Aggregate data for matching holdings
                total_value = sum(h["holding_value"] for h in matching_holdings)
                avg_risk_score = sum(h["risk_score"] for h in matching_holdings) / len(matching_holdings)
                
                holding_data["data"].append({
                    "x": ticker_to_asset_name_mapping()[value] if 'ticker' in dimension_level else value,
                    "y": round(total_value,),
                    "z": round(avg_risk_score, 2)
                })
            else:
                # Add empty data point for this value
                holding_data["data"].append({
                    "x": ticker_to_asset_name_mapping()[value] if 'ticker' in dimension_level else value,
                    "y": 0,
                    "z": ""
                })
        # Add final empty data point
        holding_data["data"].append({
            "x": "",
            "y": 0,
            "z": ""
        })

    # Define the sorting order for risk ranges  
    risk_score_range_order = ["<=2.0", "2.01 - 3.0", "3.01 - 4.0", "4.01 - 5.0", "5.01 - 6.0", "6.01 - 8.0", ">8.0"]  
    
    # Sort holdings_by_risk_range based on the predefined order of risk ranges  
    sorted_holdings_by_risk_range = {  
        range_name: holdings_by_risk_range[range_name]  
        for range_name in risk_score_range_order  
        if range_name in holdings_by_risk_range  
    }         
       
            
        # Sort the data points within each risk range by y-value (dollar value) in ascending order
        # holding_data["data"].sort(key=lambda point: point["y"]) 

    # Group by asset class for gauge chart
    # asset_class_summary = {}
    # for holding in holdings_data:
    #     asset_class = holding["Asset Class Concentration"]
    #     if asset_class not in asset_class_summary:
    #         asset_class_summary[asset_class] = {
    #             "risk_score_sum": 0,
    #             "total_value": 0,
    #             "count": 0
    #         }
        
    #     if holding["Risk Score"] is not None:
    #         asset_class_summary[asset_class]["risk_score_sum"] += holding["Risk Score"] * holding["Holding Value"]
    #         asset_class_summary[asset_class]["total_value"] += holding["Holding Value"]
    #         asset_class_summary[asset_class]["count"] += 1
    
    # # Calculate average risk score by asset class
    # gauge_items = []
    # for asset_class, summary in asset_class_summary.items():
    #     if summary["count"] > 0 and summary["total_value"] > 0:
    #         avg_risk = summary["risk_score_sum"] / summary["total_value"]
    #         gauge_items.append({
    #             "asset_class": asset_class,
    #             "risk_score": round(avg_risk, 1),
    #             "total_value": round(summary["total_value"], 1)
    #         })
    
    # Construct the final JSON structure
    chart_data = {
        "type": "json",
        "type_of_data": "chart",
        "query_type": "risk_analysis",
        "data": {
            "bubble_chart": {
                "title": f"Risk Distribution by {format_dimension(dimension_level)}",
                "x_axis_display_name": format_dimension(dimension_level),
                "y_axis_display_name": "Investment Amount (in USD)",
                "description": "Bubble size indicates risk level, position indicates asset class and value",
                "bubble_chart_type": "category",
                "items": list(sorted_holdings_by_risk_range.values())
            },
            "gauge_chart": {
                "title": "Risk Score",
                "description": "Overall portfolio risk level",
                "category": "portfolio",
                "value": "risk_score",
                "min": 0,
                "max": 10,
                "items": [{
                    "portfolio": "Your Portfolio",
                    "risk_score": round(weighted_risk_score, 2)
                }]
            }
        }
    }
    # save chart data to a file
    with open('risk_analysis_chart.json', 'w') as f:
        json.dump(chart_data, f, indent=2, cls=DateEncoder)
    
    return chart_data

def generate_returns_attribution_visualization_format(data_items, range, dimension_level="asset_class"):
    """
    Convert input data to waterfall chart format focusing on Normalized Weighted Returns.
    
    Parameters:
    input_data (dict): Input JSON data with asset class details and returns
    
    Returns:
    dict: Formatted JSON for a waterfall chart with range start and end points
    """
    # Filter out the Portfolio item and copy others
    items = [item for item in data_items if item.get(dimension_level, '').lower() != 'portfolio']
    
    # Sort items by Normalized_Weighted_Return in decreasing order
    items.sort(key=lambda x: x.get('Normalized_Weighted_Return', 0), reverse=True)
    
    # Calculate running total and create waterfall items
    waterfall_items = []
    running_total = 0
    
    for item in items:
        dimension_name = item.get(dimension_level, '')
        norm_weighted_return = round(item.get('Normalized_Weighted_Return', 0),4)
        
        start_value = running_total
        end_value = round(running_total + norm_weighted_return, 4)
        running_total = end_value
        
        # Determine value type based on the return value
        if norm_weighted_return >= 0:
            value_type = "positive"
        else:
            value_type = "negative"
        # else:
        #     value_type = "neutral"
        
        waterfall_items.append({
            "x": ticker_to_asset_name_mapping()[dimension_name] if 'ticker' in dimension_level else dimension_name,
            "y": [start_value, end_value],
            "value_type": value_type,
            # "percentage": round(item.get('Return',0) * 100,2)
        })
    
    # Add the portfolio total as the final item
    waterfall_items.append({
        "x": "Portfolio Total",
        "y": [0, running_total],
        "value_type": "total",
        # "percentage": round(sum(item.get('Return', 0) for item in items) * 100,2)

    })
    
    # Create the result structure
    result = {
        "type": "json",
        "type_of_data": "chart",
        "query_type": "returns_attribution",
        "data": {
            "waterfall_chart": {
                "title": f"Portfolio Return Attribution by {format_dimension(dimension_level)}",
                "range": range,
                "x_axis_display_name": format_dimension(dimension_level),
                "y_axis_display_name": "Normalized Weighted Return",
                "waterfall_chart_type": "category",
                "items": waterfall_items
            }
        }
    }
    with open('returns_attribution_chart.json', 'w') as f:
        json.dump(result, f, indent=2, cls=DateEncoder)
    
    return result