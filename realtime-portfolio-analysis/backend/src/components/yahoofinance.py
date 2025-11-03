from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import yfinance as yf
from dataclasses import dataclass
from curl_cffi import requests
from src.pipeline.exception import CustomException
from src.pipeline.logger import logger
import sys

router = APIRouter()

@dataclass
class YahooFinanceInfo:
    symbol: str
    legal_type: Optional[str] = None
    category: Optional[str] = None
    asset_manager: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    net_expense_ratio: Optional[float] = None
    portfolio_composition: Optional[Dict[str, float]] = None
    sector_weightings: Optional[Dict[str, float]] = None
    bond_ratings: Optional[Dict[str, float]] = None
    morningstar_rating: Optional[int] = None
    raw_info: Dict[str, Any] = None

@router.get("/yahoo-finance/{symbol}", response_model=YahooFinanceInfo)
def get_yahoo_finance_info(symbol: str) -> YahooFinanceInfo:
    try:
        # Fetch data from Yahoo Finance
        # ticker = yf.Ticker(symbol)
        # info = ticker.info

        session = requests.Session(impersonate="chrome")
        ticker = yf.Ticker(symbol,session=session)

        info = ticker.info

        # Extract relevant information
        yahoo_finance_info = YahooFinanceInfo(
            symbol=symbol,
            legal_type=info.get('quoteType'),
            category=info.get('category'),
            asset_manager=info.get('fundFamily'),
            sector=info.get('sector'),
            industry=info.get('industry'),
            net_expense_ratio=info.get('annualReportExpenseRatio'),
            morningstar_rating=info.get('morningStarOverallRating'),
            raw_info=info
        )

        # Extract portfolio composition
        composition_keys = ['cashPosition', 'stockPosition', 'bondPosition', 'otherPosition']
        yahoo_finance_info.portfolio_composition = {k: info.get(k) for k in composition_keys if k in info}

        # Extract sector weightings
        sector_weightings = {}
        for key in info:
            if key.startswith('sector') and key.endswith('Asset'):
                sector = key.replace('sector', '').replace('Asset', '')
                sector_weightings[sector] = info[key]
        yahoo_finance_info.sector_weightings = sector_weightings if sector_weightings else None

        # Extract bond ratings
        bond_ratings = {}
        for key in info:
            if key.startswith('bond') and key.endswith('Rating'):
                rating = key.replace('bond', '').replace('Rating', '')
                bond_ratings[rating] = info[key]
        yahoo_finance_info.bond_ratings = bond_ratings if bond_ratings else None

        logger.info(f"Retrieved Yahoo Finance info for symbol: {symbol}")
        return yahoo_finance_info

    except Exception as e:
        logger.error(f"Error retrieving Yahoo Finance info for symbol {symbol}: {str(e)}")
        raise CustomException(error_message=f"Failed to retrieve Yahoo Finance info for symbol {symbol}", error_details=sys.exc_info())