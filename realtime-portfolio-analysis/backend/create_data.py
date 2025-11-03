import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

import json
from src.database.database import Base
from src.database.database import SessionLocal
from src.database.models import (AssetType, AssetSector, AssetHistory, User, UserPortfolio, 
                   UserTransactions, DefaultBenchmarks, AssetClassRiskLevelMapping, RelativeBenchmark)

from curl_cffi import requests
import bs4 as bs
import re

session_yf = requests.Session(impersonate="chrome")

# Create SQLAlchemy engine and session
DATABASE_URL = "sqlite:///src/database/voicebot.sqlite3"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = SessionLocal()

# Define list of tickers to fetch data for based on the portfolio
tickers = [
    "AAPL", "JNJ", "NSRGY", "TM", "SPX",   # Stocks
    "VTI", "EFA", "SCHH",                  # ETFs
    "FTBFX", "PRMSX", "AEPGX", "VTSAX",    # Mutual Funds
    "IEF", "BNDX", "VBTLX",                # Bond ETFs
    "CASH"                                 # Cash Reserve
]

# Add the benchmark tickers that need to be added
benchmark_tickers = [
    "FTEC", "FHLC", "FSTA", "FDIS", "SPX", "ACWX", 
    "REET", "BND", "VWO", "VGIT", "AGG"
]

# Remove duplicates from the list (e.g., SPX appears in both lists)
benchmark_tickers = list(set(benchmark_tickers) - set(tickers))
all_tickers = tickers + benchmark_tickers

print(all_tickers)

# Define asset class mapping (including new benchmark tickers)
asset_class_mapping = {
    "AAPL": "U.S. Stocks",
    "JNJ": "U.S. Stocks",
    "NSRGY": "Int'l Stocks",
    "TM": "Int'l Stocks",
    "VTI": "ETFs",
    "EFA": "ETFs",
    "SCHH": "ETFs",
    "SPX": "Index",
    "VTSAX": "Mutual Funds",
    "FTBFX": "Mutual Funds",
    "PRMSX": "Mutual Funds",
    "AEPGX": "Mutual Funds",
    "VBTLX": "Bond ETFs",
    "IEF": "Bond ETFs",
    "BNDX": "Bond ETFs",
    "CASH": "Cash",
    # Add benchmark mappings
    "FTEC": "ETFs",
    "FHLC": "ETFs",
    "FSTA": "ETFs",
    "FDIS": "ETFs",
    "ACWX": "ETFs",
    "REET": "ETFs",
    "BND": "Bond ETFs",
    "VWO": "ETFs",
    "VGIT": "Bond ETFs",
    "AGG": "Bond ETFs"
}

# Asset type mapping (including new benchmark tickers)
asset_type_mapping = {
    "AAPL": "Stock",
    "JNJ": "Stock",
    "NSRGY": "Stock",
    "TM": "Stock",
    "SPX": "Stock",
    "VTI": "ETF",
    "EFA": "ETF",
    "SCHH": "ETF",
    "VTSAX": "Mutual Funds",
    "FTBFX": "Mutual Fund",
    "PRMSX": "Mutual Fund",
    "AEPGX": "Mutual Fund",
    "VBTLX": "Bond",
    "IEF": "Bond",
    "BNDX": "Bond",
    "CASH": "Cash",
    # Add benchmark mappings
    "FTEC": "ETF",
    "FHLC": "ETF",
    "FSTA": "ETF",
    "FDIS": "ETF",
    "ACWX": "ETF",
    "REET": "ETF",
    "BND": "Bond",
    "VWO": "ETF",
    "VGIT": "Bond",
    "AGG": "Bond"
}

# Asset names (adding benchmark asset names)
asset_name_mapping = {
    "AAPL": "Apple Inc.",
    "JNJ": "Johnson & Johnson",
    "NSRGY": "Nestlé S.A. (ADR)",
    "TM": "Toyota Motor Corp. (ADR)",
    "VTI": "Vanguard Total Stock Market ETF",
    "EFA": "iShares MSCI EAFE ETF",
    "SCHH": "Schwab U.S. REIT ETF",
    "SPX": "S&P 500",
    "VTSAX": "Vanguard Total Stock Mkt Idx Adm",
    "VBTLX": "Vanguard Total Bond Market Index Fund",
    "FTBFX": "Fidelity Total Bond Fund",
    "PRMSX": "T. Rowe Price Emerging Markets Stock Fund",
    "AEPGX": "American Funds EuroPacific Growth Fund",
    "IEF": "iShares 7–10 Year Treasury Bond ETF",
    "BNDX": "Vanguard Total International Bond ETF",
    "CASH": "USD Cash Reserve",
    # Add benchmark names
    "FTEC": "Fidelity MSCI Information Technology Index ETF",
    "FHLC": "Fidelity MSCI Health Care Index ETF",
    "FSTA": "Fidelity MSCI Consumer Staples Index ETF",
    "FDIS": "Fidelity MSCI Consumer Discretionary Index ETF",
    "ACWX": "iShares MSCI ACWI ex U.S. ETF",
    "REET": "iShares Global REIT ETF",
    "BND": "Vanguard Total Bond Market ETF",
    "VWO": "Vanguard FTSE Emerging Markets ETF",
    "VGIT": "Vanguard Intermediate-Term Treasury ETF",
    "AGG": "iShares Core U.S. Aggregate Bond ETF"
}

# Define relative benchmark mappings
relative_benchmark_data = [
    ('AAPL', 'Apple Inc.', 'FTEC'),
    ('JNJ', 'Johnson & Johnson', 'FHLC'),
    ('NSRGY', 'Nestlé S.A. (ADR)', 'FSTA'),
    ('TM', 'Toyota Motor Corp. (ADR)', 'FDIS'),
    ('SPX', 'S&P 500', 'SPX'),
    ('VTI', 'Vanguard Total Stock Market ETF', 'SPX'),
    ('EFA', 'iShares MSCI EAFE ETF', 'ACWX'),
    ('SCHH', 'Schwab U.S. REIT ETF', 'REET'),
    ('FTBFX', 'Fidelity Total Bond Fund', 'BND'),
    ('PRMSX', 'T. Rowe Price Emerging Markets Stock Fund', 'VWO'),
    ('AEPGX', 'American Funds EuroPacific Growth Fund', 'ACWX'),
    ('VTSAX', 'Vanguard Total Stock Mkt Idx Adm', 'SPX'),
    ('IEF', 'iShares 7–10 Year Treasury Bond ETF', 'VGIT'),
    ('BNDX', 'Vanguard Total International Bond ETF', 'AGG'),
    ('VBTLX', 'Vanguard Total Bond Market Index Fund', 'AGG')
]

# Portfolio data from the table
portfolio_data = [
    {"ticker": "CASH", "price": 1, "units": 3025, "avg_price": 1, "asset_class": "Cash"},
    {"ticker": "AAPL", "price": 185, "units": 4, "avg_price": 174.5025, "asset_class": "U.S. Stocks"},
    {"ticker": "JNJ", "price": 150, "units": 8, "avg_price": 143.4725, "asset_class": "U.S. Stocks"},
    {"ticker": "NSRGY", "price": 120, "units": 3, "avg_price": 117.34, "asset_class": "Int'l Stocks"},
    {"ticker": "TM", "price": 210, "units": 11, "avg_price": 213.2463636, "asset_class": "Int'l Stocks"},
    {"ticker": "VTI", "price": 260, "units": 20, "avg_price": 262.501, "asset_class": "ETFs"},
    {"ticker": "EFA", "price": 75, "units": 9, "avg_price": 82.71666667, "asset_class": "ETFs"},
    {"ticker": "SCHH", "price": 19, "units": 43, "avg_price": 18.53953488, "asset_class": "ETFs"},
    {"ticker": "FTBFX", "price": 10.8, "units": 154, "avg_price": 10.59584416, "asset_class": "Mutual Funds"},
    {"ticker": "PRMSX", "price": 15, "units": 38, "avg_price": 15.95342105, "asset_class": "Mutual Funds"},
    {"ticker": "AEPGX", "price": 54, "units": 72, "avg_price": 52.07763889, "asset_class": "Mutual Funds"},
    {"ticker": "IEF", "price": 94, "units": 24, "avg_price": 89.35125, "asset_class": "Bond ETFs"},
    {"ticker": "BNDX", "price": 50, "units": 74, "avg_price": 50.12594595, "asset_class": "Bond ETFs"}
]

# Transaction data from the table
transaction_data = [
    {"date": "2022-05-23", "ticker": "SCHH", "type": "Buy", "units": 49, "price_per_unit": 19.66, "actual_units": 49, "cost": 963.34},
    {"date": "2022-05-30", "ticker": "IEF", "type": "Buy", "units": 3, "price_per_unit": 94.48, "actual_units": 3, "cost": 283.44},
    {"date": "2022-06-03", "ticker": "FTBFX", "type": "Buy", "units": 61, "price_per_unit": 11.37, "actual_units": 61, "cost": 693.57},
    {"date": "2022-06-07", "ticker": "BNDX", "type": "Buy", "units": 11, "price_per_unit": 47.43, "actual_units": 11, "cost": 521.73},
    {"date": "2022-06-11", "ticker": "JNJ", "type": "Buy", "units": 6, "price_per_unit": 162.46, "actual_units": 6, "cost": 974.76},
    {"date": "2022-06-16", "ticker": "TM", "type": "Buy", "units": 4, "price_per_unit": 221, "actual_units": 4, "cost": 884},
    {"date": "2022-07-08", "ticker": "AAPL", "type": "Buy", "units": 1, "price_per_unit": 182.35, "actual_units": 1, "cost": 182.35},
    {"date": "2022-08-03", "ticker": "NSRGY", "type": "Buy", "units": 1, "price_per_unit": 126.38, "actual_units": 1, "cost": 126.38},
    {"date": "2022-08-18", "ticker": "SCHH", "type": "Sell", "units": 11, "price_per_unit": 19.49, "actual_units": -11, "cost": -214.39},
    {"date": "2022-08-25", "ticker": "VTI", "type": "Buy", "units": 3, "price_per_unit": 261.76, "actual_units": 3, "cost": 785.28},
    {"date": "2022-09-10", "ticker": "JNJ", "type": "Sell", "units": 1, "price_per_unit": 159.38, "actual_units": -1, "cost": -159.38},
    {"date": "2022-09-13", "ticker": "IEF", "type": "Buy", "units": 12, "price_per_unit": 87.17, "actual_units": 12, "cost": 1046.04},
    {"date": "2022-09-20", "ticker": "FTBFX", "type": "Buy", "units": 138, "price_per_unit": 10.47, "actual_units": 138, "cost": 1444.86},
    {"date": "2022-11-10", "ticker": "PRMSX", "type": "Sell", "units": 18, "price_per_unit": 15.73, "actual_units": -18, "cost": -283.14},
    {"date": "2022-11-22", "ticker": "PRMSX", "type": "Sell", "units": 3, "price_per_unit": 13.77, "actual_units": -3, "cost": -41.31},
    {"date": "2022-12-27", "ticker": "AAPL", "type": "Sell", "units": 1, "price_per_unit": 172.25, "actual_units": -1, "cost": -172.25},
    {"date": "2023-02-05", "ticker": "PRMSX", "type": "Sell", "units": 1, "price_per_unit": 14.26, "actual_units": -1, "cost": -14.26},
    {"date": "2023-02-17", "ticker": "IEF", "type": "Buy", "units": 9, "price_per_unit": 90.55, "actual_units": 9, "cost": 814.95},
    {"date": "2023-05-05", "ticker": "SCHH", "type": "Buy", "units": 7, "price_per_unit": 20.77, "actual_units": 7, "cost": 145.39},
    {"date": "2023-07-01", "ticker": "JNJ", "type": "Sell", "units": 3, "price_per_unit": 152.58, "actual_units": -3, "cost": -457.74},
    {"date": "2023-07-13", "ticker": "TM", "type": "Buy", "units": 2, "price_per_unit": 228.98, "actual_units": 2, "cost": 457.96},
    {"date": "2023-07-14", "ticker": "AAPL", "type": "Buy", "units": 3, "price_per_unit": 174.39, "actual_units": 3, "cost": 523.17},
    {"date": "2023-10-13", "ticker": "JNJ", "type": "Buy", "units": 7, "price_per_unit": 136.48, "actual_units": 7, "cost": 955.36},
    {"date": "2023-10-16", "ticker": "EFA", "type": "Buy", "units": 2, "price_per_unit": 81.09, "actual_units": 2, "cost": 162.18},
    {"date": "2023-10-30", "ticker": "AAPL", "type": "Buy", "units": 2, "price_per_unit": 174.34, "actual_units": 2, "cost": 348.68},
    {"date": "2023-11-01", "ticker": "EFA", "type": "Buy", "units": 8, "price_per_unit": 82.19, "actual_units": 8, "cost": 657.52},
    {"date": "2023-11-07", "ticker": "BNDX", "type": "Buy", "units": 4, "price_per_unit": 50.83, "actual_units": 4, "cost": 203.32},
    {"date": "2023-12-16", "ticker": "SCHH", "type": "Sell", "units": 23, "price_per_unit": 20.85, "actual_units": -23, "cost": -479.55},
    {"date": "2024-01-30", "ticker": "AAPL", "type": "Sell", "units": 1, "price_per_unit": 183.94, "actual_units": -1, "cost": -183.94},
    {"date": "2024-02-15", "ticker": "JNJ", "type": "Sell", "units": 2, "price_per_unit": 158.44, "actual_units": -2, "cost": -316.88},
    {"date": "2024-02-16", "ticker": "PRMSX", "type": "Buy", "units": 21, "price_per_unit": 15.29, "actual_units": 21, "cost": 321.09},
    {"date": "2024-03-23", "ticker": "NSRGY", "type": "Buy", "units": 1, "price_per_unit": 124.85, "actual_units": 1, "cost": 124.85},
    {"date": "2024-03-26", "ticker": "PRMSX", "type": "Sell", "units": 9, "price_per_unit": 15.43, "actual_units": -9, "cost": -138.87},
    {"date": "2024-04-21", "ticker": "SCHH", "type": "Sell", "units": 12, "price_per_unit": 17.55, "actual_units": -12, "cost": -210.6},
    {"date": "2024-04-28", "ticker": "AEPGX", "type": "Buy", "units": 21, "price_per_unit": 52.05, "actual_units": 21, "cost": 1093.05},
    {"date": "2024-05-14", "ticker": "EFA", "type": "Sell", "units": 1, "price_per_unit": 75.25, "actual_units": -1, "cost": -75.25},
    {"date": "2024-05-23", "ticker": "FTBFX", "type": "Sell", "units": 32, "price_per_unit": 11.84, "actual_units": -32, "cost": -378.88},
    {"date": "2024-06-04", "ticker": "AEPGX", "type": "Buy", "units": 35, "price_per_unit": 54.46, "actual_units": 35, "cost": 1906.1},
    {"date": "2024-06-16", "ticker": "BNDX", "type": "Buy", "units": 16, "price_per_unit": 50.32, "actual_units": 16, "cost": 805.12},
    {"date": "2024-07-26", "ticker": "AEPGX", "type": "Buy", "units": 20, "price_per_unit": 49.04, "actual_units": 20, "cost": 980.8},
    {"date": "2024-09-04", "ticker": "BNDX", "type": "Buy", "units": 22, "price_per_unit": 47.47, "actual_units": 22, "cost": 1044.34},
    {"date": "2024-09-10", "ticker": "NSRGY", "type": "Buy", "units": 2, "price_per_unit": 115.88, "actual_units": 2, "cost": 231.76},
    {"date": "2024-09-22", "ticker": "VTI", "type": "Buy", "units": 8, "price_per_unit": 262.46, "actual_units": 8, "cost": 2099.68},
    {"date": "2024-09-25", "ticker": "FTBFX", "type": "Sell", "units": 13, "price_per_unit": 9.83, "actual_units": -13, "cost": -127.79},
    {"date": "2024-10-10", "ticker": "VTI", "type": "Buy", "units": 2, "price_per_unit": 270.53, "actual_units": 2, "cost": 541.06},
    {"date": "2024-10-18", "ticker": "NSRGY", "type": "Sell", "units": 1, "price_per_unit": 130.97, "actual_units": -1, "cost": -130.97},
    {"date": "2025-01-04", "ticker": "AEPGX", "type": "Sell", "units": 1, "price_per_unit": 57.2, "actual_units": -1, "cost": -57.2},
    {"date": "2025-01-09", "ticker": "SCHH", "type": "Buy", "units": 33, "price_per_unit": 17.97, "actual_units": 33, "cost": 593.01},
    {"date": "2025-01-25", "ticker": "BNDX", "type": "Sell", "units": 2, "price_per_unit": 51.18, "actual_units": -2, "cost": -102.36},
    {"date": "2025-03-17", "ticker": "VTI", "type": "Sell", "units": 1, "price_per_unit": 247.68, "actual_units": -1, "cost": -247.68},
    {"date": "2025-04-18", "ticker": "AEPGX", "type": "Sell", "units": 3, "price_per_unit": 57.72, "actual_units": -3, "cost": -173.16},
    {"date": "2025-04-19", "ticker": "JNJ", "type": "Buy", "units": 1, "price_per_unit": 151.66, "actual_units": 1, "cost": 151.66},
    {"date": "2025-04-28", "ticker": "BNDX", "type": "Buy", "units": 23, "price_per_unit": 53.79, "actual_units": 23, "cost": 1237.17},
    {"date": "2025-05-02", "ticker": "TM", "type": "Buy", "units": 5, "price_per_unit": 200.75, "actual_units": 5, "cost": 1003.75},
    {"date": "2025-05-15", "ticker": "VTI", "type": "Buy", "units": 8, "price_per_unit": 258.96, "actual_units": 8, "cost": 2071.68},
    {"date": "2025-05-17", "ticker": "PRMSX", "type": "Buy", "units": 48, "price_per_unit": 15.89, "actual_units": 48, "cost": 762.72}
]
def fetch_yahoo_finance_data(ticker):
    """
    Function to fetch additional data from Yahoo Finance webpage using BS4
    """
    url = f"https://finance.yahoo.com/quote/{ticker}/holdings/"
    # try:
    session_yf = requests.Session(impersonate="chrome", verify=False)
    response = session_yf.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch data for {ticker}, status code: {response.status_code}")
        return None
    
    soup = bs.BeautifulSoup(response.text, 'html.parser')
    return soup
    # except Exception as e:
    #     print(f"Error fetching data for {ticker}: {e}")
    #     return None

def extract_sector_data(soup):
    """
    Extract sector weighting data from Yahoo Finance HTML
    """
    sector_data = []
    # try:
    # Find the section with sector weightings
    sector_section = soup.find('section', attrs={'data-testid': 'etf-sector-weightings-overview'})
    if not sector_section:
        return sector_data
    
    # Get all sector rows
    content_divs = sector_section.find_all('div', class_='content')
    
    for div in content_divs:
        try:
            sector_name = div.find('a').text.strip()
            sector_weight_text = div.find('span', class_='data').text.strip()
            sector_weight = float(sector_weight_text.replace('%', ''))
            
            sector_data.append({
                'sector_symbol': sector_name,
                'sector_name': sector_name,
                'sector_weightage': sector_weight
            })
        except Exception as e:
            print(f"Error parsing sector row: {e}")
            continue
    
    return sector_data
    # except Exception as e:
    #     print(f"Error extracting sector data: {e}")
    #     return sector_data

def extract_portfolio_composition(soup):
    """
    Extract portfolio composition data from Yahoo Finance HTML
    """
    composition_data = {}
    try:
        # Find the portfolio composition section
        composition_section = soup.find('section', attrs={'data-testid': 'portfolio-composition'})
        if not composition_section:
            return composition_data
        
        # Get all rows in the table
        rows = composition_section.find_all('tr')
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    category = cells[0].text.strip()
                    value_text = cells[1].text.strip()
                    # Convert percentage to float
                    value = float(value_text.replace('%', '')) if '%' in value_text else value_text
                    composition_data[category] = value
            except Exception as e:
                print(f"Error parsing composition row: {e}")
                continue
        
        return composition_data
    except Exception as e:
        print(f"Error extracting portfolio composition: {e}")
        return composition_data

def extract_bond_ratings(soup):
    """
    Extract bond ratings data from Yahoo Finance HTML
    """
    bond_ratings = {}
    try:
        # Find the bond ratings section
        ratings_section = soup.find('section', attrs={'data-testid': 'bond-ratings'})
        if not ratings_section:
            return bond_ratings
        
        # Get all rows in the table
        rows = ratings_section.find_all('tr')
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    rating = cells[0].text.strip()
                    value_text = cells[1].text.strip()
                    # Handle cases where value is '--'
                    if value_text == '--':
                        value = 0.0
                    else:
                        # Convert percentage to float
                        value = float(value_text.replace('%', '')) if '%' in value_text else value_text
                    bond_ratings[rating] = value
            except Exception as e:
                print(f"Error parsing bond rating row: {e}")
                continue
        
        return bond_ratings
    except Exception as e:
        print(f"Error extracting bond ratings: {e}")
        return bond_ratings

def create_relative_benchmark_table():
    """
    Create the relative_benchmarks table and insert data
    """
    try:
        # Create the RelativeBenchmark table if it doesn't exist
        RelativeBenchmark.__table__.create(session.get_bind(), checkfirst=True)
        
        # Clear existing data if any
        session.query(RelativeBenchmark).delete()
        session.commit()
        
        # Insert the benchmark mappings
        for ticker, name, benchmark in relative_benchmark_data:
            benchmark_entry = RelativeBenchmark(
                asset_ticker=ticker,
                asset_name=name,
                relative_benchmark=benchmark
            )
            session.add(benchmark_entry)
            
        session.commit()
        print("Successfully created and populated the relative_benchmarks table")
        
    except Exception as e:
        session.rollback()
        print(f"Error creating relative_benchmarks table: {e}")

def fetch_and_insert_data():
    # First, clear existing data if needed
    session.query(UserTransactions).delete()
    session.query(UserPortfolio).delete()
    session.query(AssetHistory).delete()
    session.query(AssetSector).delete()
    session.query(DefaultBenchmarks).delete()
    session.query(User).delete()
    session.query(AssetType).delete()
    session.query(AssetClassRiskLevelMapping).delete()
    session.commit()
    
    # Create the relative_benchmarks table and insert benchmark mappings
    create_relative_benchmark_table()
    
    # Fetch data for multiple tickers at once (exclude CASH)
    real_tickers = [t for t in all_tickers if t != "CASH"]  # Use all_tickers instead of just tickers
    tickers_data = yf.Tickers(" ".join(real_tickers), session=session_yf)
    
    print("Tickers Data", tickers_data)
    # Get historical price data for the last year
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=5)
    
    # Download historical data for all tickers
    print(f"Downloading historical data for {len(real_tickers)} tickers...")
    historical_data = yf.download(" ".join(real_tickers), start=start_date, end=end_date, session=session_yf)
    
    print("Historical data fetched successfully.")
    
    # Create a dictionary to map tickers to their asset IDs
    ticker_to_id = {}
    
    # Create special CASH asset first
    cash_asset = AssetType(
        asset_ticker="CASH",
        asset_name="USD Cash Reserve",
        asset_class="Cash",
        net_expense_ratio=0.0,
        morningstar_rating=None,
        maturity_date=None,
        one_yr_volatility=0.0,
        similar_asset=None,
        category="Cash",
        asset_manager=None,
        portfolio_composition=json.dumps({"Cash": 100.0}),
        legal_type="Cash"
    )
    session.add(cash_asset)
    session.commit()
    ticker_to_id["CASH"] = cash_asset.asset_id
    
    # Process each ticker (excluding CASH which we handled separately)
    for ticker in real_tickers:
        print(f"Processing {ticker}...")
        # try:
        # Get ticker info from yfinance
        ticker_info = tickers_data.tickers[ticker].info if ticker in tickers_data.tickers else {}
        if ticker_info:
            print(f"Ticker info for {ticker}: {list(ticker_info.keys())[:10]}...")
        else:
            print(f"No yfinance info available for {ticker}, using defaults")
            ticker_info = {}
        
        # Fetch additional data from Yahoo Finance webpage
        soup = fetch_yahoo_finance_data(ticker)
        
        # Extract sector weightings, portfolio composition, and bond ratings
        sector_data = []
        portfolio_composition = {}
        bond_ratings = {}
        
        # if soup:
        sector_data = extract_sector_data(soup)
        portfolio_composition = extract_portfolio_composition(soup)
        bond_ratings = extract_bond_ratings(soup)
        
        print(f"Extracted sectors for {ticker}: {len(sector_data)} sectors")
        print(f"Extracted portfolio composition for {ticker}: {portfolio_composition}")
        print(f"Extracted bond ratings for {ticker}: {bond_ratings}")
            
        # Create AssetType entry
        asset = AssetType(
            asset_ticker=ticker,
            asset_name=asset_name_mapping.get(ticker, ticker_info.get('longName', ticker_info.get('shortName', ticker))),
            asset_class=asset_class_mapping.get(ticker, "Other"),
            net_expense_ratio=ticker_info.get('annualReportExpenseRatio'),
            morningstar_rating=ticker_info.get('morningStarRating'),
            maturity_date=None,  # Would need conversion if available
            one_yr_volatility=ticker_info.get('beta'),
            similar_asset=None,  # Not provided in this dataset
            category=ticker_info.get('category'),
            asset_manager=ticker_info.get('fundFamily'),
            portfolio_composition=json.dumps(portfolio_composition) if portfolio_composition else None,
            bond_rating=None,  # Will be updated below if data is available
            legal_type=asset_type_mapping.get(ticker)
        )
        
        # Add and commit to get the asset_id
        session.add(asset)
        session.commit()
        
        # Store the asset ID for later use
        ticker_to_id[ticker] = asset.asset_id
        
        # Handle sector data from the Web scraping
        if sector_data:
            for sector_item in sector_data:
                sector_entry = AssetSector(
                    asset_id=asset.asset_id,
                    sector_symbol=sector_item['sector_symbol'],
                    sector_name=sector_item['sector_name'],
                    sector_weightage=sector_item['sector_weightage']
                )
                session.add(sector_entry)
        # Fall back to yfinance sector data if needed
        elif ticker_info.get('sectorWeightings'):
            try:
                for sector_item in ticker_info.get('sectorWeightings', [])[:10]:  # Limit to top 10 sectors
                    if isinstance(sector_item, dict):
                        for sector, weight in sector_item.items():
                            sector_entry = AssetSector(
                                asset_id=asset.asset_id,
                                sector_symbol=sector,
                                sector_name=sector,
                                sector_weightage=weight * 100 if weight < 1 else weight
                            )
                            session.add(sector_entry)
            except Exception as e:
                print(f"Error processing sectors for {ticker}: {e}")
        
        # Add bond ratings data if available
        if bond_ratings:
            # Convert the bond ratings dictionary to a float value or store as JSON
            if all(isinstance(v, (int, float)) for v in bond_ratings.values() if v is not None):
                # Option 1: Calculate an average or weighted value
                values = [v for v in bond_ratings.values() if isinstance(v, (int, float))]
                if values:
                    asset.bond_rating = sum(values) / len(values)
            else:
                # Option 2: Store as JSON
                asset.bond_rating = float(list(bond_ratings.values())[0]) if bond_ratings else None
            
            session.commit()
        
        # Add historical price data
        try:
            # Check if the ticker exists in the historical data
            ticker_history = historical_data['Close'][ticker].dropna() if ticker in historical_data['Close'].columns else None
            
            if ticker_history is not None and not ticker_history.empty:
                for date_idx, close_price in ticker_history.items():
                    if isinstance(close_price, (int, float)) and close_price > 0:
                        history_entry = AssetHistory(
                            asset_id=asset.asset_id,
                            date=date_idx.date(),
                            close_price=close_price
                        )
                        session.add(history_entry)
            else:
                print(f"No historical data available for {ticker}")
        except Exception as e:
            print(f"Error processing history for {ticker}: {e}")
        
        # Commit all the entries for this asset
        session.commit()
            
        # except Exception as e:
        #     session.rollback()
        #     print(f"Error processing {ticker}: {e}")
    
    # Add asset class risk level mappings
    risk_mappings = [
        {"invst_type": "U.S. Stocks", "volatility_range_start": 15, "volatility_range_end": 25, "risk_level": 4},
        {"invst_type": "Int'l Stocks", "volatility_range_start": 18, "volatility_range_end": 30, "risk_level": 5},
        {"invst_type": "ETFs", "volatility_range_start": 12, "volatility_range_end": 20, "risk_level": 3},
        {"invst_type": "Mutual Funds", "volatility_range_start": 10, "volatility_range_end": 18, "risk_level": 3},
        {"invst_type": "Bond ETFs", "volatility_range_start": 5, "volatility_range_end": 12, "risk_level": 2},
        {"invst_type": "Cash", "volatility_range_start": 0, "volatility_range_end": 1, "risk_level": 1},
    ]
    
    for mapping in risk_mappings:
        risk_entry = AssetClassRiskLevelMapping(**mapping)
        session.add(risk_entry)
    
    session.commit()
    
    # Create a user
    user = User(
        name="John Doe",
        username="johndoe",
        dob=date(1990, 1, 1),
        phone_number="12345678901"
    )
    
    session.add(user)
    session.commit()
    
    # Add user transactions from the provided data
    for trans in transaction_data:
        # Convert string date to date object
        trans_date = datetime.strptime(trans["date"], "%Y-%m-%d").date()
        
        # Get asset_id for the ticker
        asset_id = ticker_to_id.get(trans["ticker"])
        
        if asset_id:
            # Create transaction record
            transaction = UserTransactions(
                user_id=user.user_id,
                asset_id=asset_id,
                trans_type="BUY" if trans["type"] == "Buy" else "SELL",
                date=trans_date,
                units=trans["units"],
                price_per_unit=trans["price_per_unit"],
                cost=abs(trans["cost"])  # Store as positive number
            )
            session.add(transaction)
        else:
            print(f"Warning: Asset ID not found for ticker {trans['ticker']}")
    
    session.commit()
    
    # Add portfolio entries from the provided data
    for port in portfolio_data:
        asset_id = ticker_to_id.get(port["ticker"])
        
        if asset_id:
            # Calculate investment amount based on average price and units
            investment_amount = port["avg_price"] * port["units"]
            
            portfolio = UserPortfolio(
                user_id=user.user_id,
                asset_id=asset_id,
                asset_total_units=port["units"],
                avg_cost_per_unit=port["avg_price"],
                investment_amount=investment_amount
            )
            session.add(portfolio)
        else:
            print(f"Warning: Asset ID not found for ticker {port['ticker']}")
    
    session.commit()
    print("Data insertion completed!")

if __name__ == "__main__":
    fetch_and_insert_data() 