# Cell 1: Imports and Load API Key from .env
import os
from dotenv import load_dotenv
import requests
import datetime

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv('FINNHUB_API_KEY')
BASE_URL = 'https://finnhub.io/api/v1'

if not API_KEY:
    raise ValueError("API key not found. Make sure you have a .env file with FINNHUB_API_KEY set.")

# Cell 2: Define the API Request Function
def get_company_news(ticker: str, from_date: str, to_date: str) -> list:
    """
    Fetch company news from Finnhub API.
    
    Parameters:
    - ticker (str): Stock ticker symbol (e.g., 'AAPL').
    - from_date (str): Start date in YYYY-MM-DD format.
    - to_date (str): End date in YYYY-MM-DD format.
    
    Returns:
    - List of news articles (dicts)
    """
    url = f"{BASE_URL}/company-news"
    params = {
        'symbol': ticker,
        'from': from_date,
        'to': to_date,
        'token': API_KEY
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

# Cell 3: Display News Utility Function
# def display_news(news: list, limit: int = 5):
#     """
#     Nicely prints out the company news headlines.
    
#     Parameters:
#     - news (list): List of news article dictionaries.
#     - limit (int): Number of articles to display.
#     """
    
#     for item in news[:limit]:
#         date = datetime.datetime.fromtimestamp(item['datetime']).strftime('%Y-%m-%d %H:%M')
#         print(f"Date: {date}")
#         print(f"Headline: {item['headline']}")
#         print(f"Source: {item['source']}")
#         print(f"URL: {item['url']}")
#         print(f"Summary: {item['summary']}")
#         print("="*80)
    
#     return news[:limit]
