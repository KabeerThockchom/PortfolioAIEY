from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketState
from sqlalchemy.orm import Session
# from passlib.context import CryptContext 
from sqlalchemy import func, and_, or_, distinct, case, literal, text, desc
from src.database.database import SessionLocal
from src.database.models import User
from pydantic import BaseModel
from typing import List
from src.pipeline.exception import CustomException
from src.pipeline.logger import logger
from src.components.prompt_data import PROMPT
from src.database.models import *
from src.components.helper_functions import *
from src.components.filter_helper_functions import *
from src.components.benchmark_returns import get_index_returns
from src.components.news_tool_functions import *
from src.components.document_index import AsyncDocumentIndex
from src.components.tool_schemas import PortfolioToolSchemas
import update_asset_history_table as uaht
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import pandas as pd
import sys
import asyncio
import uuid
import json
import os
import pathlib
import base64
import httpx
from openai import AzureOpenAI

#imports for tavilly search api
from tavily import TavilyClient

#Pipecat imports
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.adapters.schemas.tools_schema import AdapterType, ToolsSchema
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams
)
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.openai_realtime_beta import (
    InputAudioNoiseReduction,
    AzureRealtimeBetaLLMService,
    InputAudioTranscription,
    OpenAIRealtimeBetaLLMService,
    SemanticTurnDetection,
    TurnDetection,
    SessionProperties,
)
from pipecat.services.azure.llm import AzureLLMService
from pipecat.services.azure.tts import AzureTTSService
from pipecat.services.azure.stt import AzureSTTService, Language
from pipecat.services.llm_service import FunctionCallParams

from pipecat.processors.aggregators.openai_llm_context import (
    OpenAILLMContext,
)

router = APIRouter()

STATIC_FILES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# Load environment variables
load_dotenv()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic model for user input
class UserCreate(BaseModel):
    name: str
    username: str
    email: str
    phone_number: str
    dob: date
    password: str

# Pydantic model for user output
class UserOut(BaseModel):
    user_id: int
    name: str
    username: str
    email: str
    phone_number: str
    dob: date

    class Config:
        from_attributes = True

class ResponseModel(BaseModel):  
    data: UserOut  # The user data  
    message: str  # Success or other message    
prompt = PROMPT   

# Global dictionary to store active WebSocket connections
active_connections = {}

# Catch-all route to handle client-side routing
# @router.get("/{full_path:path}", response_class=HTMLResponse)
# async def catch_all(full_path: str, request: Request):
#     if full_path.startswith("ws") or full_path == "favicon.ico":
#         return {"detail": "Not Found"}
#     try:
#         with open(f"{STATIC_FILES_PATH}/index.html", "r") as f:
#             return HTMLResponse(content=f.read())
#     except FileNotFoundError:
#         return HTMLResponse(content="<h1>React app not found</h1><p>Make sure you've built the React application and set the correct path.</p>", status_code=404)
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)
    
def frontend_log_filter(record):
    """Only allow log records with extra.frontend == True to pass."""
    return record["extra"].get("frontend", False) is True

def serialize_value(val):
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return val

def get_dynamic_enum_values():
    db = SessionLocal()
    try:
        # Get the unique list of tickers from database
        tickers = db.query(distinct(AssetType.asset_ticker)).filter(AssetType.asset_ticker.isnot(None)).all()
        return [ticker[0] for ticker in tickers]
    finally:
        db.close()

portfolio_holding_flag = False
def get_portfolio_summary(user_id: int, use_realtime_prices: bool = True):
    """
    Get portfolio summary for a user with live stock prices.

    Args:
        user_id: User ID
        use_realtime_prices: If True, fetches live prices from yfinance (default: True)

    Returns:
        dict with 'table' (portfolio rows) and 'total' (aggregated values)
    """
    # setting global flag to send the cash balance once the summary is retrieved
    global portfolio_holding_flag
    portfolio_holding_flag = True

    db = SessionLocal()

    # If using real-time prices, fetch them first
    realtime_prices = {}
    if use_realtime_prices:
        # Get all tickers for this user
        tickers = db.query(AssetType.asset_ticker).join(
            UserPortfolio, AssetType.asset_id == UserPortfolio.asset_id
        ).filter(
            UserPortfolio.user_id == user_id,
            AssetType.asset_ticker != 'CASH'
        ).all()
        symbols = [ticker[0] for ticker in tickers]
        if symbols:
            realtime_prices = get_realtime_prices_bulk(symbols)

    latest_price_subquery = (
    db.query(
        AssetHistory.asset_id,
        func.max(AssetHistory.date).label('latest_date')
    )
    .group_by(AssetHistory.asset_id)
    .subquery()
    )

    # Main query with rounding
    query = (
        db.query(
            User.user_id.label('Account Number'),
            AssetType.asset_name.label('Asset Name'),
            AssetType.asset_class.label('Investment Type'),
            AssetType.concentration.label('Concentration'),
            AssetType.asset_ticker.label('Ticker'),
            func.round(UserPortfolio.asset_total_units,2).label('Quantity'),
            case(
                (AssetType.asset_class == 'Cash', literal(1.0)),
                else_=func.round(UserPortfolio.avg_cost_per_unit, 2)
            ).label('Avg. Cost'),
            func.round(UserPortfolio.investment_amount, 2).label('Purchase Cost'),
            case(
                (AssetType.asset_class == 'Cash', literal(1.0)),
                else_=func.round(AssetHistory.close_price, 2)
            ).label('Current Price'),
            case(
                (AssetType.asset_class == 'Cash', UserPortfolio.investment_amount),
                else_=func.round(UserPortfolio.asset_total_units * AssetHistory.close_price, 2)
            ).label('Current Value'),
            case(
                (AssetType.asset_class == 'Cash', literal(0.0)),
                else_=func.round((UserPortfolio.asset_total_units * AssetHistory.close_price) - 
                        UserPortfolio.investment_amount, 2)
            ).label('P&L'),
            case(
                (AssetType.asset_class == 'Cash', literal(0.0)),
                else_=func.round(((AssetHistory.close_price / UserPortfolio.avg_cost_per_unit) - 1) * 100, 2)
            ).label('Percentage Change')
        )
        .join(UserPortfolio, User.user_id == UserPortfolio.user_id)
        .join(AssetType, UserPortfolio.asset_id == AssetType.asset_id)
        .outerjoin(latest_price_subquery, AssetType.asset_id == latest_price_subquery.c.asset_id)
        .outerjoin(AssetHistory, (AssetHistory.asset_id == latest_price_subquery.c.asset_id) & 
                            (AssetHistory.date == latest_price_subquery.c.latest_date))
        .filter(User.user_id == user_id)
        .order_by(
            AssetType.asset_class,
            AssetType.concentration,
            AssetType.asset_name
        )
    )

    # Execute the query and get the results
    rows = query.all()

    # Convert query results to list of dictionaries
    table_data = [dict(row._mapping) for row in rows]

    # Fix CASH row to show available balance (subtract pending buy orders)
    for row_data in table_data:
        if row_data.get('Ticker') == 'CASH':
            # Use centralized cash balance calculation
            available_cash = calculate_available_cash_balance(user_id, db)
            logger.info(f"Portfolio Summary CASH fix - User {user_id}: Available cash = ${available_cash:.2f}")
            row_data['Quantity'] = available_cash
            row_data['Purchase Cost'] = available_cash
            row_data['Current Value'] = available_cash
            logger.info(f"Updated CASH row: Quantity={row_data['Quantity']}, Current Value={row_data['Current Value']}")
            break

    # Update with real-time prices if available
    if use_realtime_prices and realtime_prices:
        for row_data in table_data:
            ticker = row_data.get('Ticker')
            if ticker in realtime_prices and ticker != 'CASH':
                rt_price = realtime_prices[ticker]
                quantity = row_data.get('Quantity', 0)
                avg_cost = row_data.get('Avg. Cost', 0)

                # Update current price and recalculate values
                row_data['Current Price'] = rt_price
                row_data['Current Value'] = round(quantity * rt_price, 2)
                row_data['P&L'] = round((quantity * rt_price) - row_data.get('Purchase Cost', 0), 2)
                if avg_cost > 0:
                    row_data['Percentage Change'] = round(((rt_price / avg_cost) - 1) * 100, 2)

    # Calculate totals
    total_purchase_cost = sum(row.get('Purchase Cost', 0) for row in table_data)
    total_current_value = sum(row.get('Current Value', 0) for row in table_data)
    total_pnl = total_current_value - total_purchase_cost
    total_percentage_change = (total_current_value / total_purchase_cost - 1) * 100 if total_purchase_cost != 0 else 0

    result = {}
    result["table"] = table_data

    # Add overall totals to the result dictionary
    result["total"] = {
        'total_purchase_cost': round(total_purchase_cost, 2),
        'total_current_value': round(total_current_value, 2),
        'total_pnl': round(total_pnl, 2),
        'total_percentage_change': round(total_percentage_change, 2)
        }

    db.close()
    return result

def get_order_book_status(user_id: int, db):
    order_status_order = {
            'Under Review': 1,
            'Placed': 2,
            'Cancelled': 3
        }
    order_details = db.query(OrderBook).filter(OrderBook.user_id == user_id).order_by(
        case(
            {status: order_status_order[status] for status in order_status_order},
            value=OrderBook.order_status,
            else_=4  # Default case for any unexpected status
        )
    ).all()

    order_details_json = [
        {c.name: serialize_value(getattr(order, c.name)) for c in order.__table__.columns if c.name not in ['asset_id', 'user_id','unit_price','description']}
        for order in order_details
    ]

    return order_details_json
    
def query_to_dataframe(query):
    results = query.all()
    columns = [desc['name'] for desc in query.column_descriptions]
    data = [dict(zip(columns, row)) for row in results]
    return pd.DataFrame(data)

@router.get("/api/users/", response_model=List[UserOut])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        users = db.query(User).offset(skip).limit(limit).all()
        logger.info(f"Retrieved {len(users)} users")
        return users
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        raise CustomException(error_message="Failed to retrieve users", error_details=sys)

@router.get("/api/users/{user_id}", response_model=UserOut)
def read_user(user_id: int, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user is None:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        logger.info(f"Retrieved user: {db_user.username}")
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {str(e)}")
        raise CustomException(error_message=f"Failed to retrieve user {user_id}", error_details=sys)

#Authenticate user api end point
@router.get("/api/users", response_model=ResponseModel)  
def authenticate_user(email_id: str, password: str, db: Session = Depends(get_db)):  
    try:  
        # Fetch user by email  
        db_user = db.query(User).filter(User.email == email_id).first()  
        if db_user is None:  
            logger.warning(f"User not found: {email_id}")  
            raise HTTPException(status_code=404, detail="User not found")  
          
        # Verify the password  
        # if not pwd_context.verify(password, db_user.hashed_password):
        if password != db_user.password:  
            logger.warning(f"Invalid password for user: {email_id}")  
            raise HTTPException(status_code=401, detail="Invalid password")  
        
        logger.info(f"Authenticated user: {db_user.username}")
        return {"data": db_user, "message": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error authenticating user {email_id}: {str(e)}")
        raise CustomException(error_message=f"Failed to authenticate user {email_id}", error_details=e)

@router.get("/api/reset_db")
async def reset_database(user_id: int,db: Session = Depends(get_db)):
    try:
        db.query(OrderBook).delete()

        cash_asset_id = db.query(AssetType.asset_id).filter(AssetType.asset_ticker == 'CASH').scalar()

        user_portfolio = db.query(UserPortfolio).filter(UserPortfolio.user_id == user_id, UserPortfolio.asset_id == cash_asset_id).first()

        user_portfolio.investment_amount = 3025
        user_portfolio.asset_total_units = 3025
        db.commit()

        logger.bind(frontend=True).info("Starting refresh_asset_history_table asynchronously...")  
        asyncio.create_task(run_refresh_asset_history_table())  # Run the function asynchronously

        logger.bind(frontend=True).info("Database reset successfully, asset history table refresh in progress.")
        return {"message": "success"}
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise CustomException(error_message="Failed to reset database", error_details=e)

async def run_refresh_asset_history_table():  
    """Async wrapper for refresh_asset_history_table."""  
    await asyncio.to_thread(uaht.refresh_asset_history_table) 

@router.get("/api/cash_balance")
def get_cash_balance(user_id: int, db: Session = Depends(get_db)):
    """
    Get available cash balance for a user.

    This endpoint uses calculate_available_cash_balance() which subtracts pending
    "Under Review" buy orders from the total CASH balance.

    ALL code displaying cash balance MUST use this calculation to ensure consistency
    across header, portfolio table, and order summary.
    """
    try:
        # Use the centralized cash balance calculation function
        cash_balance = calculate_available_cash_balance(user_id, db)

        logger.info(f"Retrieved cash balance for user {user_id}: {cash_balance}")

        return {"cash_balance": cash_balance}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving cash balance for user {user_id}: {str(e)}")
        raise CustomException(error_message=f"Failed to retrieve cash balance for user {user_id}", error_details=e)

@router.get("/api/portfolio_summary")
def get_portfolio_summary_api(user_id: int, realtime: bool = True):
    """
    Get portfolio summary with real-time prices.

    Args:
        user_id: User ID
        realtime: If True, fetches live prices from yfinance (default: True)

    Returns:
        Portfolio summary with table data and totals
    """
    try:
        result = get_portfolio_summary(user_id=user_id, use_realtime_prices=realtime)
        logger.info(f"Retrieved portfolio summary for user {user_id} (realtime={realtime})")
        return result
    except Exception as e:
        logger.error(f"Error retrieving portfolio summary for user {user_id}: {str(e)}")
        raise CustomException(error_message=f"Failed to retrieve portfolio summary for user {user_id}", error_details=e)

@router.get("/api/bank_accounts")
def get_bank_accounts(user_id: int, db: Session = Depends(get_db)):
    try:
        bank_accounts = db.query(UserBankAccount).filter(
            UserBankAccount.user_id == user_id,
            UserBankAccount.is_active == 1
        ).all()

        if not bank_accounts:
            logger.info(f"No bank accounts found for user {user_id}")
            return {"bank_accounts": []}

        accounts_list = []
        for account in bank_accounts:
            accounts_list.append({
                "bank_account_id": account.bank_account_id,
                "bank_name": account.bank_name,
                "account_number": account.account_number,
                "account_type": account.account_type,
                "available_balance": round(account.available_balance, 2)
            })

        logger.info(f"Retrieved {len(accounts_list)} bank accounts for user {user_id}")
        return {"bank_accounts": accounts_list}
    except Exception as e:
        logger.error(f"Error retrieving bank accounts for user {user_id}: {str(e)}")
        raise CustomException(error_message=f"Failed to retrieve bank accounts for user {user_id}", error_details=e)

@router.post("/api/transfer_funds")
def transfer_funds(user_id: int, bank_account_id: int, amount: float, db: Session = Depends(get_db)):
    try:
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Transfer amount must be greater than zero")

        # Get the bank account
        bank_account = db.query(UserBankAccount).filter(
            UserBankAccount.bank_account_id == bank_account_id,
            UserBankAccount.user_id == user_id,
            UserBankAccount.is_active == 1
        ).first()

        if not bank_account:
            raise HTTPException(status_code=404, detail="Bank account not found")

        # Check if bank has sufficient balance
        if bank_account.available_balance < amount:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient funds in bank account. Available: ${bank_account.available_balance:.2f}"
            )

        # Get the cash asset
        cash_asset_id = db.query(AssetType.asset_id).filter(AssetType.asset_ticker == 'CASH').scalar()
        if not cash_asset_id:
            raise HTTPException(status_code=404, detail="Cash asset not found")

        # Get or create user's cash portfolio entry
        user_cash_portfolio = db.query(UserPortfolio).filter(
            UserPortfolio.user_id == user_id,
            UserPortfolio.asset_id == cash_asset_id
        ).first()

        if not user_cash_portfolio:
            # Create new cash portfolio entry
            user_cash_portfolio = UserPortfolio(
                user_id=user_id,
                asset_id=cash_asset_id,
                asset_total_units=amount,
                avg_cost_per_unit=1.0,
                investment_amount=amount
            )
            db.add(user_cash_portfolio)
        else:
            # Update existing cash portfolio
            user_cash_portfolio.investment_amount += amount
            user_cash_portfolio.asset_total_units += amount

        # Deduct from bank account
        bank_account.available_balance -= amount

        # Commit the transaction
        db.commit()

        logger.info(f"Transferred ${amount} from bank account {bank_account_id} to brokerage for user {user_id}")

        return {
            "success": True,
            "message": f"Successfully transferred ${amount:.2f} to your brokerage account",
            "new_cash_balance": round(user_cash_portfolio.investment_amount, 2),
            "bank_balance_remaining": round(bank_account.available_balance, 2)
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error transferring funds for user {user_id}: {str(e)}")
        raise CustomException(error_message=f"Failed to transfer funds for user {user_id}", error_details=e)

@router.get("/api/stock_quote/{symbol}")
def get_stock_quote(symbol: str):
    try:
        import yfinance as yf
        from curl_cffi import requests
        from datetime import datetime

        # Create session with browser impersonation
        session = requests.Session(impersonate="chrome")
        ticker = yf.Ticker(symbol, session=session)

        # Get ticker info
        info = ticker.info

        # Get current price - try multiple sources
        current_price = None
        if 'currentPrice' in info and info['currentPrice']:
            current_price = info['currentPrice']
        elif 'regularMarketPrice' in info and info['regularMarketPrice']:
            current_price = info['regularMarketPrice']
        elif 'previousClose' in info and info['previousClose']:
            current_price = info['previousClose']

        if current_price is None:
            # Fallback: try to get from history
            hist = ticker.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]

        if current_price is None:
            raise HTTPException(status_code=404, detail=f"Unable to fetch price for symbol {symbol}")

        # Get additional quote data
        quote_data = {
            "symbol": symbol.upper(),
            "current_price": round(float(current_price), 2),
            "previous_close": round(float(info.get('previousClose', current_price)), 2),
            "open": round(float(info.get('open', current_price)), 2),
            "day_high": round(float(info.get('dayHigh', current_price)), 2),
            "day_low": round(float(info.get('dayLow', current_price)), 2),
            "volume": info.get('volume', 0),
            "market_cap": info.get('marketCap', 0),
            "name": info.get('longName', symbol.upper()),
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Retrieved stock quote for {symbol}: ${current_price}")
        return quote_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stock quote for {symbol}: {str(e)}")
        raise CustomException(error_message=f"Failed to fetch stock quote for {symbol}", error_details=e)

# Function to send JSON data through a specific WebSocket connection
async def send_json_to_websocket(phonenumber: str, data: dict):
    print("Sending data to WebSocket for phone number:", phonenumber)
    if phonenumber in active_connections:
        websocket = active_connections[phonenumber]
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(data)
        else:
            print(f"WebSocket for {phonenumber} is not in a connected state")
    else:
        print(f"WebSocket for {phonenumber} not found")    

##################################################################

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection_uuid = str(uuid.uuid4())
    query_params = websocket.query_params
    phonenumber = query_params.get("phonenumber")  # Get the 'phonenumber' parameter
    voice_id = query_params.get("voice")  # Get the 'voice_id' parameter
    realtime = query_params.get("realtime", "true")
    if not voice_id:
        voice_id = "alloy"
    if not phonenumber:
        await websocket.close(code=1008, reason="Phone number is required")
        return
    await websocket.accept()
    active_connections[phonenumber] = websocket
     # --- Real-time logger Setup ---
    log_sink_id = None
    
    async def websocket_log_sink(message):
        """Loguru sink function to send *filtered* logs over WebSocket."""
        try:
            log_record = message.record
            # print(f"Log record: {log_record}")  # Debugging line to see the log record structure
            # Prepare base log entry
            log_entry_data = {
                "type": log_record['level'].name,  # Convert log level to lowercase
                "datetime": log_record["time"].isoformat(),
                "message": log_record["message"]
            }
            # Check for bound context data and include it
            if "context_data" in log_record["extra"]:
                log_entry = {
                    "type": "rag_context", # Specific type for context
                    "data": log_record["extra"]["context_data"]
                }
            else:
                 # Standard log message
                 log_entry = {
                     "type": "json" if log_record['extra'].get('log_type', 'Text') == 'Json' else "log",
                     "type_of_data": log_record['extra'].get('log_type_of_data', 'string'),
                     'query_type': log_record['extra'].get('query_type', 'session_logs'),
                     "data": log_entry_data
                 }
 
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(log_entry))
        except WebSocketDisconnect:
             logger.warning("Log sink: WebSocket disconnected while trying to send log.")
        except Exception as e:
            print(f"Error in websocket log sink: {e}", file=sys.stderr)
                       
    log_sink_id = logger.add(
        websocket_log_sink,
        level="DEBUG",
        filter=frontend_log_filter, # Apply our custom filter
        enqueue=True,
        serialize=True
    )
    logger.info(f"Added *frontend* log sink ID: {log_sink_id} for client {websocket.client}")
    logger.bind(frontend=True).info(f"Starting session for {phonenumber}")  

    schemas = PortfolioToolSchemas()

    authenticate_user_tool_function = schemas.authenticate_user_tool()
    user_holding_tool_function = schemas.user_holding_tool()
    aggregation_tool_function = schemas.aggregation_tool()
    portfolio_benchmark_tool_function = schemas.portfolio_benchmark_tool()
    relative_performance_tool_function = schemas.relative_performance_tool()
    risk_score_tool_function = schemas.risk_score_tool()
    attribution_returns_tool_function = schemas.attribution_returns_tool()
    news_tool_function = schemas.news_tool()
    fund_fact_sheet_download_tool_function = schemas.fund_fact_sheet_download_tool()
    fact_sheet_query_tool_function = schemas.fund_fact_sheet_query_tool()
    place_trade_tool_function = schemas.place_trade_tool()
    update_trade_tool_function = schemas.update_trade_tool()
    confirm_trade_tool_function = schemas.confirm_trade_tool()
    check_order_status_tool_function = schemas.check_order_status_tool()
    cancel_order_tool_function = schemas.cancel_order_tool()
    update_cash_balance_tool_function = schemas.update_cash_balance_tool()
    get_bank_accounts_tool_function = schemas.get_bank_accounts_tool()
    transfer_from_bank_tool_function = schemas.transfer_from_bank_tool()
    get_price_trend_tool_function = schemas.get_price_trend_tool()

    tools = ToolsSchema(
            standard_tools=[authenticate_user_tool_function,
                             user_holding_tool_function, 
                             aggregation_tool_function, 
                             portfolio_benchmark_tool_function,
                             relative_performance_tool_function,
                             risk_score_tool_function,
                             attribution_returns_tool_function,
                             news_tool_function,
                             fund_fact_sheet_download_tool_function,
                             fact_sheet_query_tool_function,
                             place_trade_tool_function,
                             update_trade_tool_function,
                             confirm_trade_tool_function,
                             check_order_status_tool_function,
                             cancel_order_tool_function,
                             update_cash_balance_tool_function,
                             get_bank_accounts_tool_function,
                             transfer_from_bank_tool_function,
                             get_price_trend_tool_function],)

    # Configure transport
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_out_enabled=True,
            audio_in_enabled=True,
            add_wav_header=True,
            vad_analyzer=SileroVADAnalyzer(sample_rate=16000,params=VADParams(
                threshold=0.9,
                min_speech_duration_ms=500,
                min_silence_duration_ms=1000
            )),
            audio_in_passthrough=True,
            serializer=ProtobufFrameSerializer(),
        )
    )  


    try:
        session_properties = SessionProperties(
            input_audio_transcription=InputAudioTranscription(model="whisper-1"),
            voice=voice_id,
            turn_detection=TurnDetection(silence_duration_ms=1000),
            # tools=tools_ovr,
            instructions=PROMPT,
        )

        if realtime == "true":

            # Initialize the Gemini Multimodal Live model
            llm = AzureRealtimeBetaLLMService(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                base_url=os.getenv("AZURE_OPENAI_API_BASE"),
                session_properties=session_properties,
                start_audio_paused=False,
            )
        else:
            llm = AzureLLMService(
                api_key=os.getenv("AZURE_OPENAI_API_KEY_GPT4O"),
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                model="gpt-4o",
            )    
        logger.configure(extra={"uuid": connection_uuid,
                            "model":"gpt-4o-realtime"})
        # llm.register_function("fund_information_tool", get_answers_from_rag)
        llm.register_function("authenticate_user_tool", authenticate_user_def)
        llm.register_function("user_holding_tool", get_user_holdings)
        
        llm.register_function("aggregation_tool", get_aggregation_info)
        llm.register_function("portfolio_benchmark_tool", get_portfolio_benchmark)
        llm.register_function("relative_performance_tool", get_relative_performance)
        llm.register_function("risk_score_tool", get_risk_score)
        llm.register_function("attribution_returns_tool", get_attribution_return)
        llm.register_function("news_tool", get_news)
        llm.register_function("fund_fact_sheet_download_tool", get_fund_fact_sheet)
        llm.register_function("fund_fact_sheet_query_tool", get_fact_sheet_query_answer)
        llm.register_function("place_trade_tool", place_trade)
        llm.register_function("update_trade_tool", update_trade)
        llm.register_function("confirm_trade_tool", confirm_trade)
        llm.register_function("cancel_order_tool", cancel_order)
        llm.register_function("update_cash_balance_tool", update_cash_balance)
        llm.register_function("get_bank_accounts_tool", get_bank_accounts)
        llm.register_function("transfer_from_bank_tool", transfer_from_bank)
        llm.register_function("get_price_trend_tool", get_price_trend)

        message = [{"role": "system", "content": f"""Start by introducing yourself.
                User's phone number is '{phonenumber}'. Ask him for his date of birth for authentication."""}]

        context = OpenAILLMContext(message,tools)
        
        context_aggregator = llm.create_context_aggregator(context)

        if realtime == "true":
            # Use in pipeline
            pipeline = Pipeline([
                transport.input(),  # Speech-to-text
                context_aggregator.user(),
                llm,
                transport.output(),
                context_aggregator.assistant(),
            ])
        else: 
            # Configure service
            tts = AzureTTSService(
                api_key=os.getenv("AZURE_OPENAI_API_KEY_GPT4O"),
                region="northcentralus",
                # voice="en-US-AvaMultilingualNeural",
                # voice = "en-US-JennyNeural",
                voice = "en-US-AndrewMultilingualNeural",
                params=AzureTTSService.InputParams(
                    language=Language.EN_US,
                    rate="1.1",
                    style="cheerful"
                )
            )
            
            # Configure service
            stt = AzureSTTService(
                api_key=os.getenv("AZURE_OPENAI_API_KEY_GPT4O"),
                region="northcentralus",
                language=Language.EN_US,
                sample_rate=16000,
                channels=1
            )

            # Use in pipeline
            pipeline = Pipeline([
                transport.input(),  # Speech-to-text
                stt,
                context_aggregator.user(),
                llm,
                tts,
                transport.output(),
                context_aggregator.assistant(),
            ])    
        
        # Run pipeline
        task = PipelineTask(
                pipeline,
                params=PipelineParams(
                    audio_in_sample_rate=16000,
                    audio_out_sample_rate=16000,
                    allow_interruptions=True,
                    enable_metrics=True,
                    enable_usage_metrics=True,
                ),
                 
            )
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            logger.bind(frontend=True).info("Client connection established, preparing session.")
            await task.queue_frames([context_aggregator.user().get_context_frame()])
            
        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            logger.bind(frontend=True).info("Client disconnected")
            logger.info("Client disconnected")
            await task.cancel()      
            
        @transport.event_handler("on_session_timeout")
        async def on_session_timeout(transport, client):
            logger.info("Session timeout")

        # Run the pipeline
        await PipelineRunner(handle_sigint=False, force_gc=True).run(task)
    except WebSocketDisconnect as e:
         logger.warning(f"Client {websocket.client} disconnected forcefully: {e.code} {e.reason}")
    except Exception as e:
        logger.error(f"An error occurred in websocket endpoint: {e}")
        logger.bind(frontend=True).critical(f"Session error: {e}")
        if 'task' in locals() and not task.has_finished():
            await task.cancel()
    finally:
        # --- Logging Cleanup ---
        if log_sink_id is not None:
            try:
                logger.info(f"Removing log sink ID: {log_sink_id} for client {websocket.client}")
                logger.remove(log_sink_id)
            except ValueError:
                logger.warning(f"Log sink {log_sink_id} already removed or invalid.")
        # --- End Logging Cleanup ---    

async def authenticate_user_def(params:FunctionCallParams):
    phonenumber = params.arguments['phonenumber']
    dob = params.arguments['date_of_birth']
    session = SessionLocal()
    if not phonenumber:
        await params.result_callback("Invalid input: Phone number is required")
    logger.info(f"Authenticating user with phone number: {phonenumber}")
    logger.bind(frontend=True).info(f"Authenticating user {phonenumber}...") # Log to frontend

    user = session.query(User).filter(User.phone_number == phonenumber).first()
    if user:
        # if str(user.dob) != dob:
        #     logger.bind(frontend=True).error(f"User authentication failed for phone number: {phonenumber}")
        #     await params.result_callback("User authentication failed")
        #     return
        
        user_id = session.query(User.user_id).filter(User.phone_number == phonenumber).scalar()
        result = get_portfolio_summary(user_id=user_id)

        await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"table","query_type":"user_portfolio","data": result})
        
        logger.info(f"User authenticated successfully: with user_id - {user.user_id}, Name - {user.name}")
        # logger.bind(frontend=True).success(json.loads(result_json))
        await params.result_callback(f"User authenticated successfully: {user.user_id}, {user.name}")
    else:
        logger.bind(frontend=True).error(f"User authentication failed for phone number: {phonenumber}")
        await params.result_callback("User authentication failed")

async def get_user_holdings(params: FunctionCallParams):
    try:
        session = SessionLocal()
        user_id = params.arguments['user_id']
        phonenumber = session.query (User.phone_number).filter(User.user_id == user_id).scalar()

        result = get_portfolio_summary(user_id=user_id)
        
        await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"table","query_type":"user_portfolio","data": result})
        
        result_json = json.dumps(result)
        
        formatted_message = f"Showing user holdings table."
        await params.result_callback(f"{formatted_message} Results: {json.loads(result_json)}. Do not read out the result and use only for the context of the call")
    except Exception as e:
        logger.error(f"Error in get_user_holdings: {str(e)}")
        await params.result_callback("An error occurred while fetching user holdings. Please try again later.")
        raise CustomException(error_message="Failed to fetch user holdings", error_details=sys)
    
async def get_aggregation_info(params: FunctionCallParams):
    session = SessionLocal()
    user_id = params.arguments['user_id']
    aggregation_metric = params.arguments['aggregation_metric']
    dimension_levels = params.arguments.get("dimension_levels", ["Asset Class"])
    visualization_type = params.arguments.get('visualization_types', 'donut')
    # filter_levels = params.arguments.get('filter_level', None)
    filter_values = params.arguments.get('filter_values', None)

    dimension_levels = get_standardized_filter_dimesions(dimension_levels, tool_type="aggregation") #getting the standized values of dimension levels

    if filter_values!=None:
        filter_levels_dict = get_filter_levels_dict(session)
        filters = get_filters_dict(filter_levels_dict, filter_values) #getting the filters dictionary
    phonenumber = session.query (User.phone_number).filter(User.user_id == user_id).scalar()

    try:
        if aggregation_metric == 'total portfolio value':
            # Subquery to get the latest closing price for each asset
            latest_price_subquery = session.query(
                AssetHistory.asset_id,
                func.max(AssetHistory.date).label('max_date')
            ).group_by(AssetHistory.asset_id).subquery()

            latest_price = session.query(
                    AssetHistory.asset_id,
                    AssetHistory.close_price
                ).join(
                    latest_price_subquery,
                    and_(
                        AssetHistory.asset_id == latest_price_subquery.c.asset_id,
                        AssetHistory.date == latest_price_subquery.c.max_date
                    )
                ).subquery()

            query = session.query(
                UserPortfolio.user_id,
                AssetType.asset_class,
                AssetType.concentration,
                AssetType.asset_manager,
                AssetType.category,
                case(  
                    # If asset_class is 'Stocks', set sector_name to 'all'  
                    (AssetType.asset_class == 'Stock', literal('Stock')),
                    # If asset_class is 'Cash', set sector_name to 'Cash'  
                    (AssetType.asset_class == 'Cash', literal('Cash')),  
                    # Default: coalesce with AssetSector.sector_name or 'Cash'  
                    else_=func.coalesce(AssetSector.sector_name, 'Cash')  
                ).label('sector_name'),
                AssetType.asset_ticker,
                case(
                    (AssetType.asset_class == 'Cash', literal(1.0)),
                    else_=latest_price.c.close_price
                ).label('latest_close_price'),
                func.coalesce(AssetSector.sector_weightage, 100).label('sector_weightage'),
                UserPortfolio.asset_total_units,
                case(
                    (AssetType.asset_class == 'Cash', UserPortfolio.investment_amount),
                    else_=func.round(
                        UserPortfolio.asset_total_units * 
                        (func.coalesce(AssetSector.sector_weightage, 100)/100) * 
                        func.coalesce(latest_price.c.close_price, 0),
                        2
                    )
                ).label('weighted_value')
            ).join(
                AssetType, UserPortfolio.asset_id == AssetType.asset_id
            ).outerjoin(
                AssetSector, AssetType.asset_id == AssetSector.asset_id
            ).outerjoin(
                latest_price, AssetType.asset_id == latest_price.c.asset_id
            ).filter(
                UserPortfolio.user_id == user_id
            )

            query_df = query_to_dataframe(query)
            total_portfolio_value = query_df['weighted_value'].sum()
            
            if filter_values!=None:
                # Apply filters
                filter_conditions = []
                for column, values in filters.items():
                    if column == 'asset_class':
                        filter_conditions.append(AssetType.asset_class.in_(values))
                    elif column == 'sector':
                        filter_conditions.append(AssetSector.sector_name.in_(values))
                    elif column == 'asset_name':
                        filter_conditions.append(AssetType.asset_name.in_(values))
                    elif column == 'ticker':
                        filter_conditions.append(AssetType.asset_ticker.in_(values))
                    elif column == 'concentration':
                        filter_conditions.append(AssetType.concentration.in_(values))
                    elif column == 'asset_manager':
                        filter_conditions.append(AssetType.asset_manager.in_(values))
                    elif column == 'category':
                        filter_conditions.append(AssetType.category.in_(values)) 

                if filter_conditions:
                    query = query.filter(and_(*filter_conditions))
                    # query = query.filter(or_(*filter_conditions))
            
            query_df = query_to_dataframe(query)
            
            if len(query_df) == 0:
                # await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"table","query_type":"aggregation_level_1","data": []})
                await params.result_callback("No data found for the given filters.")
                return

            # Group by the specified dimension levels
            groupby_cols = dimension_levels
            query_df = query_df.rename({'sector_name': 'sector','asset_ticker': 'ticker'}, axis=1)
            query_df = query_df.groupby(groupby_cols).agg({'weighted_value': 'sum'}).reset_index()
            # Round the values to 2 decimal places
            query_df['weighted_value'] = query_df['weighted_value']

            query_df['percentage_value'] = (query_df['weighted_value'] / total_portfolio_value * 100)

            if filter_values!=None:
                aggregation_json(query_df,dimension_levels,list(filters.keys()))
            else:
                aggregation_json(query_df,dimension_levels)

            # Convert the DataFrame to a list of dictionaries
            results = query_df.to_dict('records')

            # Format the results
            formatted_results = []
            for result in results:
                item = {}
                for _, dimension in enumerate(dimension_levels):
                    item[dimension] = result[dimension]    
                item['percentage'] = round(result['weighted_value'], 2)
                formatted_results.append(item)

            ##logic to decide the chart type and format the results accordingly
            if len(dimension_levels) == 1:
                chart_data = transform_to_donut_chart_format_single_level(
                                    formatted_results, 
                                    label_field=dimension_levels[0],
                                    value_field='percentage',
                                    chart_type = visualization_type,
                                    title = "Portfolio Distribution by " + format_dimension(dimension_levels[0]),
                                    description = "Distribution by " + format_dimension(dimension_levels[0])
                                )
                await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"chart","query_type":"aggregation_level_1","data": chart_data})
                # logger.bind(frontend=True).bind(log_type="Json").bind(log_type_of_data="chart").success(chart_data)
            elif len(dimension_levels) == 2:
                chart_data = transform_to_donut_chart_format_double_level(
                                    formatted_results,
                                    outer_field=dimension_levels[0],
                                    inner_field=dimension_levels[1],
                                    value_field='percentage',
                                    chart_type = visualization_type,
                                    title = "Portfolio Distribution by " + format_dimension(dimension_levels[0]) + " and " + format_dimension(dimension_levels[1]),
                                    description = f"Distribution by {format_dimension(dimension_levels[0])} and {format_dimension(dimension_levels[1])}"
                                )
                print(f"Chart data for 2 levels {dimension_levels}: {chart_data}")  # Debugging line to see the chart data structure
                await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"chart","query_type":"aggregation_level_2","data": chart_data})
                # logger.bind(frontend=True).bind(log_type="Json").bind(log_type_of_data="chart").success(chart_data) 

        elif aggregation_metric == 'percentage returns':
            # Get extended data for the user
            extended_data = AssetHistory.get_extended_data(session, user_id)
            
            # Convert to DataFrame
            df = pd.DataFrame(extended_data, columns=[
                'asset_hist_id', 'asset_id', 'date', 'close_price', 'asset_class', 'asset_name','concentration',
                'asset_manager', 'category', 'ticker', 'sector', 'sector_weightage', 'asset_total_units'
            ])
            # df.to_excel('extended_data.xlsx', index=False)

            # Ensure 'date' is in datetime format
            df['date'] = pd.to_datetime(df['date'])

            # df.to_excel('extended_data.xlsx', index=False)

            # Calculate daily stock value
            if "sector" in dimension_levels:
                print("Calculating portfolio with sector weightage")
                df['portfolio'] = df['close_price'] * df['asset_total_units'] * df['sector_weightage']/100
            else:
                df = df.drop(columns=['sector','sector_weightage'], errors='ignore')
                df = df.drop_duplicates(subset=['asset_hist_id'], keep='last')
                df['portfolio'] = df['close_price'] * df['asset_total_units']    

            # Add quarter and year columns
            df['quarter'] = df['date'].dt.to_period('Q')
            df['year'] = df['date'].dt.year

            # Group by dimension levels and get the last day of each quarter
            groupby_cols = [col for col in dimension_levels if col in df.columns]

            # Get the last date of each quarter for each group
            df['last_date'] = df.groupby(groupby_cols+['year','quarter'])['date'].transform('max')
            
            # df['last_date'] = df['last_date'] - pd.Timedelta(days=1)


            # Filter to keep only the last date of each quarter for each group
            df_last_date = df[df['date'] == df['last_date']]

            # Group by and sum the stock values
            grouped = df_last_date.groupby(groupby_cols+['year','quarter','last_date'])['portfolio'].sum().reset_index()

            # Sort the grouped data
            grouped = grouped.sort_values(
                by=groupby_cols + ['last_date'],
                ascending=[True] * len(groupby_cols) + [False]  # Ascending for groupby_cols, descending for last_date
            )

            # Get top 9 rows for each group
            grouped = grouped.groupby(groupby_cols).apply(lambda x: x.nlargest(9, 'last_date')).reset_index(drop=True)

            # Sort again to ensure the final order is correct
            grouped = grouped.sort_values(
                by=groupby_cols + ['last_date'],
                ascending=[True] * len(groupby_cols) + [False]
            )

            # Calculate percentage change
            def calculate_portfolio_return(group):
                group['portfolio_return'] = group['portfolio'].pct_change(-1) * 100
                return group

            result = grouped.groupby(groupby_cols).apply(calculate_portfolio_return).reset_index(drop=True)

            # Round the percentage change to two decimal places
            result['portfolio_return'] = round(result['portfolio_return'],2)
            result = result.dropna()

            # Convert 'date' to string format
            result['last_date'] = result['last_date'].dt.strftime('%Y-%m-%d')

            # Convert 'quarter' to string format
            result['quarter'] = result['quarter'].astype(str)

            # Format the results
            formatted_results = result.to_dict('records')

            result = transform_to_stack_bar_chart_format(
                        formatted_results, 
                        title="Quarterly "+dimension_levels[0]+" Performance",
                        value_field="portfolio_return",
                        description="Portfolio returns by "+dimension_levels[0]+" across quarters"
                    )

            await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"chart","data": result})
            # logger.bind(frontend=True).bind(log_type="Json").bind(log_type_of_data="chart").success(json.dumps(result)) 

        formatted_results_json = json.dumps(formatted_results)

        # The rest of your code remains the same
        result = {
            'total_portfolio_value': round(total_portfolio_value, 2) if aggregation_metric == 'total portfolio value' else None,
            'aggregation_metric': aggregation_metric,
            'dimension_levels': dimension_levels,
            'data': json.loads(formatted_results_json)
        }
     
        result_json = json.dumps(result)

        # await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"chart","data": json.loads(formatted_results_json)})
        # logger.bind(frontend=True).success(json.loads(result_json))
        await params.result_callback(f"Your results are ready and on your screen. Results: {json.loads(result_json)}. Do not read out the result and use only for the context of the call")
    except Exception as e:
        logger.error(f"An error occurred while processing aggregation info: {e}")
        await params.result_callback(f"An error occurred while processing your request: {str(e)}")
        raise CustomException(error_message="Failed to process aggregation info", error_details=sys)
    finally:
        session.close()

# Calculate percentage change
def calculate_portfolio_return(group):
    group['portfolio_return'] = group['portfolio'].pct_change(-1) * 100
    return group

#Calculate return for line chart data
def calculate_line_chart_return(group):
    group = group.sort_values('date')
    oldest_value = group['portfolio'].iloc[0]
    group['portfolio_return'] = (group['portfolio'] / oldest_value) * 100
    return group

async def get_portfolio_benchmark(params: FunctionCallParams):
    session = SessionLocal()

    try:
        user_id = params.arguments["user_id"]
        time_history = params.arguments.get("time_history", 2)  # Default to 2 years if not provided
        dimension_levels = params.arguments.get("dimension_levels", ["all"])
        filter_values = params.arguments.get("filter_values", [])
        interval = params.arguments.get("interval", "quarterly")

        if "all" in dimension_levels:
            dimension_levels = "all"

        if "all" not in dimension_levels:
            dimension_levels = get_standardized_filter_dimesions(dimension_levels, tool_type="portfolio_benchmark")  #getting the standized values of dimension levels
        
        benchmark_against = params.arguments.get("benchmark_against", ["SPX"])  # Default to S&P 500 if not provided
        if 'all' in benchmark_against:
            benchmark_against = ['SPX', 'VTSAX', 'VBTLX']
        elif "None" in benchmark_against:
            benchmark_against = ["SPX"]  

        benchmark_indices = ['SPX', 'VTSAX', 'VBTLX']

        # Convert benchmark_against to a list if it's a single string
        if isinstance(benchmark_against, str):
            benchmark_against = [benchmark_against]

        # Check if all elements in benchmark_against are valid
        if not all(index in benchmark_indices for index in benchmark_against):
            invalid_indices = [index for index in benchmark_against if index not in benchmark_indices]
            await params.result_callback(f"Invalid benchmark index(es): {', '.join(invalid_indices)}. Currently available benchmark indices are: {', '.join(benchmark_indices)}")
            return

        if len(dimension_levels) > 1 and dimension_levels!='all':
            await params.result_callback(f"Currently available dimensions are {dimension_levels}. Please select only one of them.")
            return

        # Validate and process the input parameters
        if not user_id or not dimension_levels:
            await params.result_callback("Invalid input parameters.")
            return
        
        phonenumber = session.query(User.phone_number).filter(User.user_id == user_id).scalar()    

        extended_data = AssetHistory.get_extended_data(session, user_id)
            
        # Convert to DataFrame
        df = pd.DataFrame(extended_data, columns=[
            'asset_hist_id', 'asset_id', 'date', 'close_price', 'asset_class','asset_name', 'concentration',
            'asset_manager', 'category', 'ticker', 'sector', 'sector_weightage', 'asset_total_units'
        ])
        if len(filter_values) > 0:
            # Get filter levels dictionary
            filter_levels_dict = get_filter_levels_dict(session)
            filters = get_filters_dict(filter_levels_dict, filter_values) #getting the filters dictionary
            if filters:
                for column, values in filters.items():
                    if column in df.columns:
                        df = df[df[column].isin(values)]
                    else:
                        print(f"Warning: Column '{column}' not found in DataFrame")

        # Ensure 'date' is in datetime format
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year

        # Calculate daily stock value
        if "sector" in dimension_levels:
            df['portfolio'] = df['close_price'] * df['asset_total_units'] * df['sector_weightage']/100
        else:
            df = df.drop(columns=['sector','sector_weightage'], errors='ignore')
            df = df.drop_duplicates(subset=['asset_hist_id'], keep='last')
            df['portfolio'] = df['close_price'] * df['asset_total_units']    

        if "all" in dimension_levels and len(filter_values) == 0:
            groupby_cols = []
        elif len(filter_values)==0:
            # Group by dimension levels and get the last day of each quarter
            groupby_cols = [col for col in dimension_levels if col in df.columns]
        else:
            groupby_cols = [col for col in filters.keys() if col in df.columns]    

        if len(groupby_cols) > 1:
            await params.result_callback(f"Please select only dimension type at a time.")
            return
        
        ################################# For daily returns line chart ########################
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        date_mark = df['date'].max() - timedelta(days=365 * time_history)

        portfolio_data = df[df['date'] >= date_mark]
        portfolio_data = portfolio_data.sort_values(by=['date'], ascending=False)
        
        portfolio_data = portfolio_data.groupby(groupby_cols+['date']).agg({'portfolio': 'sum'}).reset_index()

        # portfolio_data.to_excel('portfolio_data_before_return.xlsx', index=False)
        if groupby_cols:
            portfolio_data = portfolio_data.groupby(groupby_cols).apply(calculate_line_chart_return).reset_index(drop=True)
        else:
            portfolio_data = calculate_line_chart_return(portfolio_data).reset_index(drop=True)

        portfolio_data['portfolio_return'] = round(portfolio_data['portfolio_return'],2)

        if "all" in dimension_levels and len(filter_values) == 0:
            portfolio_data['dimension'] = 'portfolio'
        # Find the index of the 'date' column
        date_index = portfolio_data.columns.get_loc('date')
        # Rename the column just before 'date' to 'dimensions'
        if date_index > 0:
            prev_column = portfolio_data.columns[date_index - 1]
            portfolio_data.rename(columns={prev_column: 'dimension'}, inplace=True)

        # portfolio_data.to_excel('portfolio_data.xlsx', index=False)

        portfolio_data = portfolio_data[['date','dimension','portfolio','portfolio_return']]
        # Convert 'date' column to datetime if it's not already
        portfolio_data['date'] = pd.to_datetime(portfolio_data['date'])

        # Extract just the date part (removing the time)
        portfolio_data['date'] = portfolio_data['date'].dt.date

        ### For Index Daily Returns
        index_asset = ['SPX', 'VTSAX', 'VBTLX']
        # Get the list of index_id for some asset type
        index_ids = session.query(AssetType.asset_id, AssetType.asset_ticker).filter(AssetType.asset_ticker.in_(index_asset)).all()

        # Extract just the asset_ids from the tuples
        asset_ids = [id_tuple[0] for id_tuple in index_ids]

        query = (session.query(AssetHistory.asset_id,
                            AssetHistory.date,
                            AssetHistory.close_price,
                            # Add other columns you need here
                            )
                .filter(AssetHistory.asset_id.in_(asset_ids))
                .filter(AssetHistory.date >= date_mark)
                .order_by(AssetHistory.date.desc()))

        # Execute the query and fetch all results
        results = query.all()

        # Convert the results to a DataFrame
        index_data= pd.DataFrame(results, columns=['asset_id', 'date', 'close_price'])  # Add other column names here

        # Add asset_ticker to the DataFrame
        id_to_ticker = {id_tuple[0]: id_tuple[1] for id_tuple in index_ids}
        index_data['asset_ticker'] = index_data['asset_id'].map(id_to_ticker)
        index_data['date'] = pd.to_datetime(index_data['date'], errors='coerce')
        index_data = index_data[index_data['date'] >= date_mark]
        index_data = index_data.sort_values(by=['date'], ascending=False)
        index_data = index_data.rename(columns={'close_price': 'portfolio','asset_ticker':'dimension'})
        index_data = index_data.groupby('dimension').apply(calculate_line_chart_return).reset_index(drop=True)

        index_data['date'] = index_data['date'].dt.date
        index_data = index_data[['date','dimension','portfolio','portfolio_return']]
        index_data = index_data[index_data['dimension'].isin(benchmark_against)]
        final_line_chart_df = pd.concat([portfolio_data, index_data], ignore_index=True)
        final_line_chart_df['portfolio_return'] = round(final_line_chart_df['portfolio_return'],2)
        final_line_chart_df = final_line_chart_df.fillna(0)
        
        def is_working_day(date):  
            """Check if the given date is a working day (Monday to Friday)."""  
            return date.weekday() < 5  # 0 = Monday, ..., 4 = Friday  
  
        def is_month_end(date):  
            """Check if the date is the last day of the month and a working day."""  
            next_day = date + timedelta(days=1)  
            return next_day.month != date.month and is_working_day(date)  
        
        def is_quarter_end(date):  
            """Check if the date is the last day of a quarter and a working day."""  
            # Quarters end in March, June, September, December  
            if is_month_end(date) and date.month in (3, 6, 9, 12):  
                return True  
            return False  
        
        def is_year_end(date):  
            """Check if the date is the last day of the year and a working day."""  
            return is_month_end(date) and date.month == 12 

        def is_week_end(row, df):
            current_date = row['date']  
            for day in range(4, -1, -1):  # 4 (Friday) to 0 (Monday)  
            # Check if the current date matches this weekday  
                if current_date.weekday() == day:  
                    # Check if there is a next day in the DataFrame  
                    next_day = current_date + pd.Timedelta(days=1)  
                    if next_day in df['date'].values:  
                        # If the next day exists in the DataFrame, it's not the last working day of the week  
                        return False  
                    # If no next day exists, this is the last working day of the week  
                    return True  
            return False  

        # Create the date_marker column
        final_line_chart_df['date_marker'] = ''

        final_line_chart_df['date_marker'] = final_line_chart_df.apply(  
            lambda row: 'Weekly' if is_week_end(row, final_line_chart_df) else '',  
            axis=1  
        ) 

        # Mark quarterly dates (overrides weekly if it's also a quarter end)
        # final_line_chart_df.loc[final_line_chart_df['date'].apply(is_quarter_end), 'date_marker'] = 'Quarterly'
        # final_line_chart_df.loc[final_line_chart_df['date'].apply(is_month_end), 'date_marker'] = 'Monthly'
        # final_line_chart_df.loc[final_line_chart_df['date'].apply(is_year_end), 'date_marker'] = 'Yearly'


        # if interval == 'weekly':
        #     lst = ['Weekly']
        # elif interval == 'monthly':
        #     lst = ['Weekly', 'Monthly']
        # elif interval == 'quarterly':
        #     lst = ['Weekly', 'Quarterly'] 
        # else:
        #     lst = ['Weekly', 'Yearly']       
        # Sort the dataframe by date if it's not already sorted
        final_line_chart_df = final_line_chart_df.sort_values('date')
        # final_line_chart_df.to_excel('final_line_chart_data_before.xlsx', index=False)
        # final_line_chart_df = final_line_chart_df[final_line_chart_df['date_marker'].isin(['Weekly']) | 
        #                             (final_line_chart_df.groupby('dimension').cumcount() == 0)]

        # final_line_chart_df = final_line_chart_df[(final_line_chart_df.groupby('dimension').cumcount() == 0)]
        ################################# End of line chart #################################

        # Set date as index
        df.set_index('date', inplace=True)
    
        all_data = []

        if 'all' not in dimension_levels:
            dimension_levels_copy = dimension_levels.copy()
            if 'sector' in dimension_levels_copy:
                dimension_levels_copy[dimension_levels_copy.index('sector')] = 'sector_name'
            if 'ticker' in dimension_levels_copy:
                dimension_levels_copy[dimension_levels_copy.index('ticker')] = 'asset_ticker' 
            #get the unique values of the dimension level column from database
            query = session.query(text(f"DISTINCT {dimension_levels_copy[0]}")).select_from(AssetType)
            unique_elements = [row[0] for row in query.all()]

            for ele in unique_elements:
                asset_data = df[df[dimension_levels[0]] == ele]
                if not asset_data.empty:
                    all_data.append(process_time_period_data(asset_data,dimension_levels, interval,time_history))
        else:
            # If dimension_levels is 'all', process the entire DataFrame
            all_data.append(process_time_period_data(df, dimension_levels, interval, time_history))
        all_data = pd.DataFrame(pd.concat(all_data, ignore_index=True))

        all_data = all_data.sort_values(['year', 'freq', 'index_name'], ascending=[False, False, True]).reset_index(drop=True)
        # all_data.to_excel("check_all_data.xlsx", index=False)
        # Calculate returns for each index
        all_data['return'] = all_data.groupby('index_name')['close_price'].pct_change(-1) * 100
        all_data['return'] = round(all_data['return'],2)
        #remove the last row
        all_data = all_data[:-1]
        # all_data.to_excel("check_all_data2.xlsx", index=False)
        # Format close price
        all_data['close_price'] = round(all_data['close_price'],2)

        # Reorder columns
        columns = ['year', 'freq', 'last_date', 'index_name', 'close_price', 'return']
        all_data = all_data[columns]
        all_data = all_data.rename(columns={'index_name': 'dimension','date':'last_date','close_price': 'portfolio','return': 'portfolio_return'})
        all_data = all_data.dropna()

        index_return_df = get_index_returns(benchmark_against,interval,time_history)

        all_data['last_date'] = pd.to_datetime(all_data['last_date'])
        index_return_df['last_date'] = pd.to_datetime(index_return_df['last_date'])

        if dimension_levels == "all" and len(filter_values) == 0:
            all_data['dimension'] = 'portfolio'
        else:
            all_data = all_data.rename(columns={dimension_levels[0]: 'dimension'})
            all_data = all_data.rename(columns={groupby_cols[0]: 'dimension'})


        result = pd.concat([all_data, index_return_df], axis=0, ignore_index=True)
        # result = result[result['portfolio_return']!=0]
        # result.to_excel('result_data.xlsx', index=False)

        # result['last_date'] = pd.to_datetime(result['last_date'], errors='coerce')
        final_line_chart_df['date'] = pd.to_datetime(final_line_chart_df['date'], errors='coerce')

        final_line_chart_df = final_line_chart_df[  
        (final_line_chart_df['date_marker'] == 'Weekly') |  # Include rows with 'Weekly' marker  
        (final_line_chart_df['date'].isin(result['last_date'])) |  # Include rows with common dates in result      
        (final_line_chart_df.groupby('dimension').cumcount() == 0)  # Include the first row in each dimension group  
        ]  

        # final_line_chart_df.to_excel('final_line_chart_data.xlsx', index=False)    

        result['last_date'] = result['last_date'].dt.strftime('%Y-%m-%d')
        final_line_chart_df['date'] = final_line_chart_df['date'].dt.strftime('%Y-%m-%d')

        result['portfolio'] = round(result['portfolio'],2)

        # result = pd.merge(result, index_return_df, on='last_date', how='inner')

        # Convert 'quarter' to string format
        result['freq'] = result['freq'].astype(str)
        result = result.drop(columns=['date_marker'], errors='ignore')
        result = result.dropna()
        # Format the results
        formatted_results = result.to_dict('records')     

        chart_data = performance_chart(result,final_line_chart_df,time_history,interval,title=f"Historical Benchmarking for last {time_history}yr")

        chart_data = json.loads(chart_data)

        await send_json_to_websocket(phonenumber, chart_data)
        # logger.bind(frontend=True).bind(log_type="Json").bind(log_type_of_data="chart").success(json.dumps(result)) 

        formatted_results_json = json.dumps(formatted_results)

        # The rest of your code remains the same
        result = {
            'dimension_levels': dimension_levels,
            'data': json.loads(formatted_results_json)
        }

        df_output = pd.DataFrame(formatted_results)
        # df_output = df_output.dropna()
        # df_output.to_excel('portfolio_performance.xlsx', index=False)
        
        result_json = json.dumps(result)

        # await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"chart","query_type":"performance","data": json.loads(result_json)})
        # logger.bind(frontend=True).success(json.loads(result_json))
        await params.result_callback(f"Your results are ready and on your screen. Results: {json.loads(result_json)}. Do not read out the result and use only for the context of the call")
    except Exception as e:
        logger.error(f"An error occurred while processing portfolio benchmark: {e}")
        await params.result_callback(f"An error occurred while processing your request: {str(e)}")
        raise CustomException(error_message="Failed to process portfolio benchmark", error_details=sys)
    finally:
        session.close()        

async def get_relative_performance(params: FunctionCallParams):
    """
    Calculate the relative performance of a user's portfolio holdings against their benchmarks.
    
    Args:
        session: SQLAlchemy database session
        user_id: The ID of the user whose portfolio we're analyzing
        time_history: Time period for the return calculation ('week', 'month', '3month', '6month', 'year', 'ytd')
    
    Returns:
        List of dictionaries with holding info, benchmark info, and comparative returns
    """
    session = SessionLocal()
    try:

        user_id = params.arguments["user_id"]

        time_history = params.arguments.get("time_history", "1year")  # Default to 1 year if not provided

        filter_values = params.arguments.get("filter_values", [])

        # Calculate start date based on time_history parameter
        today = datetime.now().date()
        
        if time_history == 'week':
            start_date = today - timedelta(days=7)
        elif time_history == 'month':
            start_date = today - relativedelta(months=1)
        elif time_history == '3month':
            start_date = today - relativedelta(months=3)
        elif time_history == '6month':
            start_date = today - relativedelta(months=6)
        elif time_history == '1year':
            start_date = today - relativedelta(years=1)
        elif time_history == '2year':
            start_date = today - relativedelta(years=2)
        elif time_history == '3year':
            start_date = today - relativedelta(years=3)
        elif time_history == '5year':
            start_date = today - relativedelta(years=5)
        elif time_history == 'ytd':
            start_date = datetime(today.year, 1, 1).date()
        else:
            start_date = today - relativedelta(years=1)
        
        # Get user portfolio holdings
        user_holdings = session.query(
            UserPortfolio.asset_id, 
            UserPortfolio.asset_total_units,
            AssetType.asset_ticker,
            AssetType.asset_name,
            AssetType.asset_class,
            AssetType.concentration,
        ).join(
            AssetType, UserPortfolio.asset_id == AssetType.asset_id
        ).filter(
            UserPortfolio.user_id == user_id,
            UserPortfolio.asset_total_units > 0
        )
        
        #checking if filter values are provided
        if len(filter_values) > 0:
            # Get filter levels dictionary
            filter_levels_dict = get_filter_levels_dict(session)
            filters = get_filters_dict(filter_levels_dict, filter_values) #getting the filters dictionary
            print(f"Filter values: {filters}")
            #check if filters is empty
            if filters:
                filter_conditions = []
                for column, values in filters.items():
                    if column == 'asset_class':
                        filter_conditions.append(AssetType.asset_class.in_(values))
                    elif column == 'asset_name':
                        filter_conditions.append(AssetType.asset_name.in_(values))
                    elif column == 'ticker':
                        filter_conditions.append(AssetType.asset_ticker.in_(values))
                    elif column == 'concentration':
                        filter_conditions.append(AssetType.concentration.in_(values))
                    elif column == 'asset_manager':
                        filter_conditions.append(AssetType.asset_manager.in_(values))
                    elif column == 'category':
                        filter_conditions.append(AssetType.category.in_(values))            
                    # Add more conditions for other columns as needed

                if filter_conditions:
                    user_holdings = user_holdings.filter(and_(*filter_conditions))

        user_holdings = user_holdings.all()

        if not user_holdings:
            await params.result_callback("No Data found for the filters.")
            return []
            
        # Get benchmark mappings from RelativeBenchmark table
        benchmark_mappings = {
            ticker: benchmark for ticker, benchmark in 
            session.query(
                RelativeBenchmark.asset_ticker,
                RelativeBenchmark.relative_benchmark
            ).all()
        }
        
        # Dictionary to store ticker to asset_id mapping
        ticker_to_asset_id = {
            asset.asset_ticker: asset.asset_id for asset in 
            session.query(AssetType.asset_ticker, AssetType.asset_id).all()
        }
        
        results = []
        
        for holding in user_holdings:
            asset_id = holding.asset_id
            asset_ticker = holding.asset_ticker
            asset_name = holding.asset_name
            
            # Skip if this asset doesn't have a benchmark mapping
            if asset_ticker not in benchmark_mappings:
                continue
                
            benchmark_ticker = benchmark_mappings[asset_ticker]
            benchmark_asset_id = ticker_to_asset_id.get(benchmark_ticker)
            
            if not benchmark_asset_id:
                continue
                
            # Get benchmark name
            benchmark_name = session.query(AssetType.asset_name).filter(
                AssetType.asset_id == benchmark_asset_id
            ).scalar()
            
            # Get historical price data for the holding
            holding_prices = session.query(
                AssetHistory.date,
                AssetHistory.close_price
            ).filter(
                AssetHistory.asset_id == asset_id,
                AssetHistory.date >= start_date
            ).order_by(AssetHistory.date).all()
            
            # Get historical price data for the benchmark
            benchmark_prices = session.query(
                AssetHistory.date,
                AssetHistory.close_price
            ).filter(
                AssetHistory.asset_id == benchmark_asset_id,
                AssetHistory.date >= start_date
            ).order_by(AssetHistory.date).all()
            
            # Skip if we don't have enough price data
            if not holding_prices or not benchmark_prices:
                continue
                
            # Calculate returns
            holding_start_price = holding_prices[0].close_price
            holding_end_price = holding_prices[-1].close_price
            benchmark_start_price = benchmark_prices[0].close_price
            benchmark_end_price = benchmark_prices[-1].close_price
            
            if holding_start_price <= 0 or benchmark_start_price <= 0:
                continue
                
            holding_return = (holding_end_price / holding_start_price - 1) * 100
            benchmark_return = (benchmark_end_price / benchmark_start_price - 1) * 100
            
            # Store results
            results.append({
                "holding_ticker": asset_ticker,
                "holding_name": asset_name,
                "benchmark_ticker": benchmark_ticker,
                "benchmark_name": benchmark_name,
                "holding_return": round(holding_return, 2),
                "benchmark_return": round(benchmark_return, 2),
                "relative_performance": round(holding_return - benchmark_return, 2),
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": today.strftime("%Y-%m-%d"),
                "period": time_history
            })
        chart_data = format_relative_performance_chart(results, range=time_history, title=f"Relative Performance of Holdings vs Benchmarks for {time_history}")

        phonenumber = session.query(User.phone_number).filter(User.user_id == user_id).scalar()

        # Send chart data via WebSocket
        await send_json_to_websocket(phonenumber, chart_data)
        
        result_json = json.dumps(results)
        
        formatted_message = f"Showing relative performance for {len(results)} holdings over {time_history} period."
        await params.result_callback(f"{formatted_message} Results: {json.loads(result_json)}. Do not read out the result and use only for the context of the call. Just say any variation of 'your chart is on the screen.'")  
    except Exception as e:
        logger.error(f"An error occurred while processing relative performance: {e}")
        await params.result_callback(f"An error occurred while processing your request: {str(e)}")
        raise CustomException(error_message="Failed to process relative performance", error_details=sys)
    finally:
        session.close()    

# def filter_data(data, dimension_levels=None, filter_values=None):
#     if not dimension_levels or not filter_values:
#         return data

#     filtered_data = data
#     for dimension in dimension_levels:
#         if dimension in filter_values:
#             filtered_data = [item for item in filtered_data if item.get(dimension) == filter_values[dimension]]
    
#     return filtered_data

async def get_risk_score(params: FunctionCallParams):
    session = SessionLocal()
    try:

        user_id = params.arguments["user_id"]

        dimension_levels = params.arguments.get("dimension_levels", ["Ticker"])
        filter_values = params.arguments.get("filter_values", [])

        print(f"Dimension levels: {dimension_levels}, Filter values: {filter_values}")

        #Default dimension_levels to ticker if not provided
        if dimension_levels is None and len(filter_values) == 0:
            dimension_levels = ['Ticker']

        dimension_levels = get_standardized_filter_dimesions(dimension_levels) #getting the standized values of dimension levels

        portfolio_query = (
            session.query(
                UserPortfolio.user_port_id,
                UserPortfolio.asset_id,
                UserPortfolio.asset_total_units,
                UserPortfolio.avg_cost_per_unit,
                AssetType.asset_ticker,
                AssetType.asset_name,
                AssetType.asset_class,
                AssetType.one_yr_volatility,
                AssetType.concentration,  # Added concentration field
                AssetType.asset_manager  # Added asset manager field
            )
            .join(AssetType, UserPortfolio.asset_id == AssetType.asset_id)
            .filter(UserPortfolio.user_id == user_id)
        )

        if len(filter_values) > 0:
            # Get filter levels dictionary
            filter_levels_dict = get_filter_levels_dict(session)
            filters = get_filters_dict(filter_levels_dict, filter_values) #getting the filters dictionary

            if filters:
                filter_conditions = []
                for column, values in filters.items():
                    if column == 'asset_class':
                        filter_conditions.append(AssetType.asset_class.in_(values))
                    elif column == 'asset_name':
                        filter_conditions.append(AssetType.asset_name.in_(values))
                    elif column == 'ticker':
                        filter_conditions.append(AssetType.asset_ticker.in_(values))
                    elif column == 'concentration':
                        filter_conditions.append(AssetType.concentration.in_(values))
                    elif column == 'asset_manager':
                        filter_conditions.append(AssetType.asset_manager.in_(values))
                    elif column == 'category':
                        filter_conditions.append(AssetType.category.in_(values))            
                    # Add more conditions for other columns as needed

                if filter_conditions:
                    portfolio_query = portfolio_query.filter(and_(*filter_conditions))
                    # user_holdings = user_holdings.filter(or_(*filter_conditions))

        holdings = portfolio_query.all()
        
        if holdings is None or len(holdings) == 0:
            await params.result_callback("No holdings found for the user.")
            return
        # Step 3: Get current prices for each holding
        result = []
        
        for holding in holdings:
            # Get the latest price for this asset
            latest_price = (
                session.query(AssetHistory.close_price)
                .filter(AssetHistory.asset_id == holding.asset_id)
                .order_by(AssetHistory.date.desc())
                .first()
            )
            if not latest_price:
                latest_price = [1]
                # continue  # Skip if no price history
            
            current_price = latest_price[0]
            
            # Step 4: Calculate holding value
            holding_value = holding.asset_total_units * current_price
            
            # Step 5: Get risk score for this asset class based on asset_class and concentration
            # Find matching risk level from asset_class_risk_level_mapping
            risk_mapping = (
                session.query(AssetClassRiskLevelMapping.risk_score)  # Use risk_score (renamed from risk_level)
                .filter(
                    AssetClassRiskLevelMapping.asset_type == holding.asset_class,  # Use asset_type (renamed from invst_type)
                    AssetClassRiskLevelMapping.concentration == holding.concentration  # Added concentration filter
                )
                .first()
            )
            
            risk_score = risk_mapping[0] if risk_mapping else None
            
            # Compile results
            result.append({
                "portfolio_id": holding.user_port_id,
                "asset_id": holding.asset_id,
                "ticker": holding.asset_ticker,
                "name": holding.asset_name,
                "asset_class": holding.asset_class,
                "concentration": holding.concentration,  # Added concentration
                "asset_manager": holding.asset_manager, # Added asset manager
                "units": holding.asset_total_units,
                "avg_cost": holding.avg_cost_per_unit,
                "current_price": current_price,
                "holding_value": holding_value,
                "volatility": holding.one_yr_volatility,
                "risk_score": risk_score
            })
        filtered_data = result.copy()
        # filtered_data = filter_data(result, dimension_levels, filter_values)
        simplified_data = []
        for holding in filtered_data:
            simplified_data.append({
                "asset_class": holding["asset_class"],
                "concentration" : holding["concentration"],
                "ticker": holding["ticker"],
                "asset_manager": holding["asset_manager"],
                "holding_value": round(holding["holding_value"], 2),
                "risk_score": holding["risk_score"]
            })
        simplified_data = pd.DataFrame(simplified_data)
        #calculate the weigthed risk score for each dimension level for the simplified data
        simplified_data['multiplied_value'] = simplified_data['holding_value'] * simplified_data['risk_score']

        simplified_data = simplified_data.groupby(dimension_levels[0]).sum(["holding_value","multiplied_value"]).reset_index()
        simplified_data['risk_score'] = round(simplified_data['multiplied_value'] / simplified_data['holding_value'],2)
        simplified_data = simplified_data.drop(columns=['multiplied_value'])
        simplified_data = simplified_data.to_dict(orient='records')

        total_value = sum(holding["holding_value"] for holding in filtered_data)
        total_risk_holding_product = sum(holding["holding_value"] * holding["risk_score"] for holding in filtered_data if holding["risk_score"] is not None)

        weighted_risk_score = total_risk_holding_product / total_value if total_value > 0 else 0

        simplified_data.sort(key=lambda x: x["holding_value"] if x["holding_value"] is not None else 0, reverse=True)

        chart_data = generate_risk_analysis_visualization_json(simplified_data, weighted_risk_score,dimension_levels[0])

        phonenumber = session.query(User.phone_number).filter(User.user_id == user_id).scalar()

        await send_json_to_websocket(phonenumber, chart_data)

        result_json = json.dumps(result)
        
        formatted_message = f"Showing risk analysis for {len(result)} holdings."
        await params.result_callback(f"{formatted_message} Results: {json.loads(result_json)}. Do not read out the result and use only for the context of the call")
    except Exception as e:
        logger.error(f"An error occurred while processing risk score: {e}")
        await params.result_callback(f"An error occurred while processing your request: {str(e)}")
        raise CustomException(error_message="Failed to process risk score", error_details=sys)
    finally:
        session.close()    

async def get_attribution_return(params: FunctionCallParams):
    session = SessionLocal()
    try:

        user_id = params.arguments["user_id"]
        dimension_levels = params.arguments.get("dimension_levels", ["Asset Class"])  # Default to all dimensions if not provided
        time_period = params.arguments.get("time_period", "current")  # Default to current if not provided
        filter_values = params.arguments.get("filter_values", [])

        dimension_levels = get_standardized_filter_dimesions(dimension_levels, tool_type="attribution_return")

        if len(dimension_levels) > 1:
            await params.result_callback(f"Currently available dimensions are {dimension_levels}. Please select only one of them.")
            return
        
        phonenumber = session.query(User.phone_number).filter(User.user_id == user_id).scalar()

        # Get reference date based on time period
        today = datetime.now().date()
        reference_date = today
        
        if time_period == "1month" or time_period == "past month" or time_period == "1m":
            reference_date = today - timedelta(days=30)
        elif time_period == "3months" or time_period == "past 3 months" or time_period == "3m":
            reference_date = today - timedelta(days=90)
        elif time_period == "6months" or time_period == "past 6 months" or time_period == "6m":
            reference_date = today - timedelta(days=180)
        elif time_period == "1year" or time_period == "past year" or time_period == "1y":
            reference_date = today - timedelta(days=365)
        elif time_period == "2years" or time_period == "past 2 years" or time_period == "2y":
            reference_date = today - timedelta(days=730)
        elif time_period == "3years" or time_period == "past 3 years" or time_period == "3y":
            reference_date = today - timedelta(days=1095)
        elif time_period == "5years" or time_period == "past 5 years" or time_period == "5y":
            reference_date = today - timedelta(days=1825)
        
        print(f"Reference date for attribution return calculation: {reference_date}")
        
        # Subquery to get the latest closing price for each asset
        latest_price_subquery = session.query(
            AssetHistory.asset_id,
            func.max(AssetHistory.date).label('max_date')
        ).group_by(AssetHistory.asset_id).subquery()

        latest_price = session.query(
                AssetHistory.asset_id,
                AssetHistory.close_price
            ).join(
                latest_price_subquery,
                and_(
                    AssetHistory.asset_id == latest_price_subquery.c.asset_id,
                    AssetHistory.date == latest_price_subquery.c.max_date
                )
            ).subquery()
        
        # Subquery to get the historical price closest to the reference date
        if time_period != "current":
            # First find the closest date for each asset
            historical_date_subquery = session.query(
                AssetHistory.asset_id,
                func.min(
                    func.abs(func.julianday(AssetHistory.date) - func.julianday(reference_date))
                ).label('min_date_diff'),
                func.max(AssetHistory.date).filter(
                    func.abs(func.julianday(AssetHistory.date) - func.julianday(reference_date)) == 
                    func.min(func.abs(func.julianday(AssetHistory.date) - func.julianday(reference_date)))
                ).label('closest_date')
            ).group_by(AssetHistory.asset_id).subquery()

            # Then get the price for that closest date
            historical_price = session.query(
                AssetHistory.asset_id,
                AssetHistory.close_price.label('historical_close_price'),
                AssetHistory.date.label('historical_date')
            ).join(
                historical_date_subquery,
                and_(
                    AssetHistory.asset_id == historical_date_subquery.c.asset_id,
                    AssetHistory.date == historical_date_subquery.c.closest_date
                )
            ).subquery()
        
        query = session.query(
            UserPortfolio.user_id,
            UserPortfolio.avg_cost_per_unit,
            AssetType.asset_class,
            AssetType.concentration,
            AssetType.asset_manager,
            AssetType.category,
            AssetSector.sector_name.label('sector'),
            AssetType.asset_ticker.label('ticker'),
            latest_price.c.close_price.label('latest_close_price'),
            AssetSector.sector_weightage,
            UserPortfolio.asset_total_units,
            func.round(
                        UserPortfolio.asset_total_units * 
                        (func.coalesce(AssetSector.sector_weightage, 100)/100) * 
                        func.coalesce(latest_price.c.close_price, 0),
                        2
            ).label('weighted_value')
        ).join(
                AssetType, UserPortfolio.asset_id == AssetType.asset_id
        ).outerjoin(
                AssetSector, AssetType.asset_id == AssetSector.asset_id
        ).outerjoin(
                latest_price, AssetType.asset_id == latest_price.c.asset_id
        )
        
        # Join with historical price if time period is specified
        if time_period != "current":
            query = query.outerjoin(
                historical_price, AssetType.asset_id == historical_price.c.asset_id
            ).add_columns(
                historical_price.c.historical_close_price,
                historical_price.c.historical_date
            )

        query = query.filter(UserPortfolio.user_id == user_id)

        # Checking if filter values are provided
        if len(filter_values) > 0:
            # Get filter levels dictionary
            filter_levels_dict = get_filter_levels_dict(session)
            filters = get_filters_dict(filter_levels_dict, filter_values) #getting the filters dictionary
            # Check if filters is empty
            if filters:
                filter_conditions = []
                for column, values in filters.items():
                    if column == 'asset_class':
                        filter_conditions.append(AssetType.asset_class.in_(values))
                    elif column == 'asset_name':
                        filter_conditions.append(AssetType.asset_name.in_(values))
                    elif column == 'ticker':
                        filter_conditions.append(AssetType.asset_ticker.in_(values))
                    elif column == 'concentration':
                        filter_conditions.append(AssetType.concentration.in_(values))
                    elif column == 'asset_manager':
                        filter_conditions.append(AssetType.asset_manager.in_(values))
                    elif column == 'category':
                        filter_conditions.append(AssetType.category.in_(values))            
                    # Add more conditions for other columns as needed

                if filter_conditions:
                    query = query.filter(and_(*filter_conditions))
                    # query = query.filter(or_(*filter_conditions))

        query_df = query_to_dataframe(query)
        
        if len(query_df) == 0:
            await params.result_callback("No Data found for the filters.")
            return
        # Calculate return based on time period
        if time_period == "current":
            # Use avg_cost_per_unit as the baseline for return calculation (original functionality)
            query_df['Return'] = (query_df['latest_close_price'] - query_df['avg_cost_per_unit']) / query_df['avg_cost_per_unit']
            query_df['Investment'] = query_df['asset_total_units'] * query_df['avg_cost_per_unit']
        else:
            # Use historical price as baseline for return calculation
            query_df['Return'] = (query_df['latest_close_price'] - query_df['historical_close_price']) / query_df['historical_close_price']
            query_df['Investment'] = query_df['asset_total_units'] * query_df['historical_close_price']
            # Handle NaN values where historical data isn't available
            missing_historical = query_df['historical_close_price'].isna()
            if missing_historical.any():
                print(f"Warning: {missing_historical.sum()} assets missing historical data, falling back to avg_cost")
                query_df.loc[missing_historical, 'Return'] = (
                    query_df.loc[missing_historical, 'latest_close_price'] - 
                    query_df.loc[missing_historical, 'avg_cost_per_unit']
                ) / query_df.loc[missing_historical, 'avg_cost_per_unit']
                query_df.loc[missing_historical, 'Investment'] = (
                    query_df.loc[missing_historical, 'asset_total_units'] * 
                    query_df.loc[missing_historical, 'avg_cost_per_unit']
                )

        # Weighted return
        query_df['Weighted_Return'] = query_df['Return'] * query_df['Investment']

        # Aggregate at chosen dimension
        agg_query_df = query_df.groupby(dimension_levels).agg({
            'Return': 'mean',  # Not used in chart, just for info
            'Investment': 'sum',
            'Weighted_Return': 'sum'
        }).reset_index()

        # Calculate final normalized weighted return
        total_investment = agg_query_df['Investment'].sum()
        if total_investment > 0:
            agg_query_df['Normalized_Weighted_Return'] = agg_query_df['Weighted_Return'] / total_investment
        else:
            agg_query_df['Normalized_Weighted_Return'] = 0

        # Sort descending for waterfall chart
        agg_query_df = agg_query_df.sort_values(by='Normalized_Weighted_Return', ascending=False)
        agg_query_df = agg_query_df.fillna(0) 
        # agg_query_df.to_excel('attribution_return_data.xlsx', index=False)
        
        result = agg_query_df.to_dict('records')

        chart_data = generate_returns_attribution_visualization_format(result, range=time_period, dimension_level=dimension_levels[0])

        await send_json_to_websocket(phonenumber, chart_data)
        await params.result_callback(f"Your attribution return results are ready and on your screen. Results: {json.loads(json.dumps(chart_data))}. Do not read out the result and use only for the context of the call. Just say any variation of: 'your chart is on the screen.'")
    except Exception as e:
        logger.error(f"Error in get_returns: {str(e)}")
        await params.result_callback(f"Sorry, I encountered an error while processing your request. Please try again.")
        raise CustomException(error_message="Failed to process attribution return", error_details=sys)
    finally:
        session.close()    

async def get_news(params: FunctionCallParams):
    try:
        ticker = params.arguments.get("ticker", None)
        user_id = params.arguments.get("user_id", None)

        session = SessionLocal()

        if ticker  == None:
            await params.result_callback("Please provide a valid ticker symbol to search for news.")
        
        today = date.today()
        week_ago = today - timedelta(days=7)

        # Fetch and display news
        news_items = get_company_news(ticker, week_ago.isoformat(), today.isoformat())

        phonenumber = session.query(User.phone_number).filter(User.user_id == user_id).scalar()

        await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"text","query_type":"news","data": news_items[:3]})
        await params.result_callback(f"Here's what I found about '{ticker}':\n\n{news_items[:3]}. Please say this response in short and concise manner.")
    
    except Exception as e:
        logger.error(f"Error in get_news: {str(e)}")
        await params.result_callback(f"Sorry, I encountered an error while searching for news about '{ticker}'. Please try again.")
        raise CustomException(error_message="Failed to fetch news", error_details=sys)
    finally:
        session.close()

# async def get_news(params: FunctionCallParams):
#     ticker = params.arguments["ticker"]
#     user_id = params.arguments["user_id"]

#     session = SessionLocal()

#     if ticker == None:
#         return await params.result_callback("Please provide a valid ticker symbol to search for news.")
    
#     # try:
#     # Initialize Tavily client with API key
#     tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
#     # Search for relevant news with Tavily
#     search_result = tavily_client.search(
#         query=query,
#         # search_depth="basic",
#         # include_images=False,
#         include_raw_content="text",
#         max_results=10
#     )
    
#     print(f"Search results for query '{query}': {search_result}")
#     # Process search results
#     results = []
#     for result in search_result.get("results", []):
#         results.append({
#             "title": result.get("title", ""),
#             "url": result.get("url", ""),
#             "content": result.get("content", "") if result.get("raw_content", "") == None else result.get("raw_content", ""),
#             "published_date": result.get("published_date", "")
#         })
    
#     # Use Azure GPT-4o to summarize the results
#     summarized_response = await summarize_news_results(query, results)
    
#     phonenumber = session.query (User.phone_number).filter(User.user_id == user_id).scalar()

#     #send the response to the websocket
#     await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"text","query_type":"news","data": summarized_response})

#     # Return the summary to the user
#     await params.result_callback(f"Here's what I found about '{query}':\n\n{summarized_response}. Please say this response in short and ask the user to read the news on the screen. Do not read out the result and use only for the context of the call.")
#     # except Exception as e:
#     #     logger.error(f"Error in news tool: {str(e)}")
#     #     await params.result_callback(f"Sorry, I encountered an error while searching for news about '{query}'. Please try again.")

# async def summarize_news_results(query, results):
#     # Initialize Azure OpenAI client
#     client = AzureOpenAI(
#         api_key=os.getenv("AZURE_OPENAI_API_KEY_GPT4O"),
#         api_version="2024-12-01-preview",
#         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
#     )
#     # Prepare content for summarization
#     content_text = f"Query: {query}\n\nSearch Results:\n"
#     for i, result in enumerate(results, 1):
#         content_text += f"\n{i}. TITLE: {result['title']}\n"
#         content_text += f"DATE: {result['published_date']}\n"
#         content_text += f"URL: {result['url']}\n"
#         content_text += f"CONTENT: {result['content'][:1000]}...\n"  # Limit content length
    
#     # Create prompt for summarization
#     prompt = f"""
#     Based on the search results below, provide a comprehensive and informative answer to the query.
#     Include relevant facts, dates, and information from multiple sources when possible.
#     If the search results don't contain enough information, acknowledge the limitations.
    
#     {content_text}
    
#     Provide a well-organized, factual summary that answers the query: "{query}"
#     """
#     messages=[
#         {"role": "system", "content": "You are a news agent which provides the comprehensive and informative answer to the user query based on the search results."},
#         {"role": "user", "content": prompt},
#     ]
#     # Get summary from Azure GPT-4o
#     response = client.chat.completions.create(
#         model="gpt-4o",
#         messages = messages
#     )
    
#     return response.choices[0].message.content

async def get_fund_fact_sheet(params: FunctionCallParams):
    try:
        user_id = params.arguments["user_id"]
        ticker = params.arguments.get("ticker", None)
        if ticker is None:
            await params.result_callback("Please provide a valid ticker symbol to fetch the fund fact sheet.")

        if ticker not in ["AEPGX", "BNDX", "EFA", "FTBFX", "IEF", "PRMSX", "VTI", "SCHH"]:
            await params.result_callback("Please provide a valid ticker symbol.")
        session = SessionLocal()

        phonenumber = session.query(User.phone_number).filter(User.user_id == user_id).scalar()
        # Fetch the fund fact sheet from the azure blob storage
        await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"text","query_type":"fund_fact_sheet","data": {"message":f"Fund Document for:{ticker}", "file_link": f"https://rtpastorage.blob.core.windows.net/fund-sheets/{ticker}-AR.pdf"}})

        await params.result_callback(f"Say I have fetched the fund fact sheet for {ticker}. You can download it from the link on the screen.")
    except Exception as e:
        logger.error(f"Error in get_fund_fact_sheet: {str(e)}")
        await params.result_callback(f"Sorry, I encountered an error while fetching the fund fact sheet for '{ticker}'. Please try again.")
        raise CustomException(error_message="Failed to fetch fund fact sheet", error_details=sys)
    finally:
        session.close()

async def get_fact_sheet_query_answer(params: FunctionCallParams):
    try:

        index_obj = AsyncDocumentIndex()
        user_id = params.arguments["user_id"]
        query = params.arguments.get("query", None)
        ticker = params.arguments.get("ticker", None)
        if ticker is None:
            await params.result_callback("Please provide a valid ticker symbol to fetch the fund fact sheet.")

        if ticker not in ["AEPGX", "BNDX", "EFA", "FTBFX", "IEF", "PRMSX", "VTI", "SCHH"]:
            await params.result_callback("Please provide a valid ticker symbol.")
            return
        session = SessionLocal()
        phonenumber = session.query(User.phone_number).filter(User.user_id == user_id).scalar()
        # logger.bind(frontend=True).info(f"Searching knowledge base for: '{query[:50]}'")

        # await params.result_callback("Please wait while I search the knowledge base for your query...")

        top_k_results = await index_obj.query_index_async(query, ticker, k=20)  # Get top 16 results
        
        # Assuming 'top_k_results' is your new single dataframe response
        text_context_for_ui = []
        image_context_for_ui = []
        temp_counter = 0
        for result in top_k_results:
            if result["source_type"] == "figure" and temp_counter < 3:
                try:
                    # Get the raw path string
                    raw_path_str = result["image_path"]
                    # Replace backslashes with forward slashes
                    normalized_path_str = raw_path_str.replace("\\", "/")
                    
                    # --- Optional but Recommended: Use pathlib ---
                    image_path = pathlib.Path(normalized_path_str)
                    #image_path = result["image_path"]
                    with open(image_path, "rb") as img_file:
                        image_bytes = img_file.read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    mime_type = "image/jpeg"  # Adjust if needed based on actual image type

                    image_context_for_ui.append({
                        "image_base64": f"data:{mime_type};base64,{image_base64}",
                        "caption": result.get("content", "No caption"),
                        "file_name": result.get("file_name", "Unknown")
                    })
                except Exception as e:
                    logger.error(f"Error processing image for UI: {e}")
                    image_context_for_ui.append({
                        "image_base64": None,  # Indicate error or missing image
                        "caption": f"Error loading image: {result.get('content', 'Unknown')}",
                        "file_name": result.get("file_name", "Unknown")
                    })
            else:
                text_context_for_ui.append(result["content"])
            temp_counter += 1    
        
        rag_context_payload = {
            "query": query,
            "text_context": text_context_for_ui,
            "image_context": image_context_for_ui,
        }

        # Bind the payload and log. The filter ensures this goes to the frontend sink.
        logger.bind(frontend=True, context_data=rag_context_payload).info("RAG context retrieved.")

        logger.bind(frontend=True).info("RAG context retrieved.")

        # await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"string","query_type":"session_logs","data": {"type": "INFO", "datetime":""}})

        if top_k_results:
            print("\n--- Generating Multimodal RAG Response ---")
            # final_answer = index_obj.get_multimodal_rag_response(query, top_k_results)
            final_answer = await index_obj.get_multimodal_rag_response_async(query, top_k_results)

            logger.bind(frontend=True).success(f"Answer generated : '{final_answer}'")
            
            final_answer = json.loads(json.dumps({"Answer from RAG": final_answer}))
        else:
            final_answer = json.loads(json.dumps({"Answer from RAG": "No results found for your query."})) 
        
        await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"text","query_type":"rag_response","data": final_answer,"file_link": f"https://rtpastorage.blob.core.windows.net/fund-sheets/{ticker}-AR.pdf"})

        await params.result_callback(f"This is the answer from the RAG. {final_answer}")
    except Exception as e:
        logger.error(f"Error in get_fact_sheet_query_answer: {str(e)}")
        await params.result_callback(f"Sorry, I encountered an error while processing your query. Please try again.")
        raise CustomException(error_message="Failed to process fact sheet query answer", error_details=sys)
    finally:
        session.close()
        logger.bind(frontend=True).info("get_fact_sheet_query_answer completed.")        

async def place_trade(params: FunctionCallParams):
    db = SessionLocal()
    try:
        # Initialize response_data with None values
        response_data = {
            "symbol": None,
            "action": None,
            "order_type": None,
            "quantity": None,
            "limit_price": None,
            "trade": "Stocks/ETFs/Mutual Fund",
            "account": "Brokerage Account",
            "order_date": None,
            "order_status": "Under Review",
            "unit_price": None,
            "amount": None,
            "cash_balance": None,
        }

        user_id = params.arguments.get("user_id")
        phonenumber = db.query(User.phone_number).filter(User.user_id == user_id).scalar()

        #get the cash balance of the user using centralized function
        cash_balance = calculate_available_cash_balance(user_id, db)
        response_data["cash_balance"] = cash_balance

        # Update response_data with initial values
        response_data["symbol"] = params.arguments.get("symbol")
        response_data["action"] = params.arguments.get("action")
        response_data["order_type"] = params.arguments.get("order_type")
        response_data["quantity"] = params.arguments.get("quantity")
        response_data["limit_price"] = params.arguments.get("limit_price")

        if not response_data["symbol"] or not response_data["quantity"]:
            error_msg = "Please provide a valid symbol and quantity to place a trade."
            await send_json_to_websocket(phonenumber, {
                "type": "log",
                "type_of_data": "text",
                "query_type": "trade_response",
                "data": {**response_data, "error": error_msg},
                "all_data": get_order_book_status(user_id, db)
            })
            await params.result_callback(error_msg)
            return

        if not response_data["quantity"] or int(response_data["quantity"]) <= 0:
            error_msg = "Please provide a valid quantity to place a trade."
            await send_json_to_websocket(phonenumber, {
                "type": "log",
                "type_of_data": "text",
                "query_type": "trade_response",
                "data": {**response_data, "error": error_msg},
                "all_data": get_order_book_status(user_id, db)
            })
            await params.result_callback(error_msg)
            return

        if response_data["order_type"] not in ["market", "limit"]:
            error_msg = "Please provide a valid order type (market or limit)."
            await send_json_to_websocket(phonenumber, {
                "type": "log",
                "type_of_data": "text",
                "query_type": "trade_response",
                "data": {**response_data, "error": error_msg},
                "all_data": get_order_book_status(user_id, db)
            })
            await params.result_callback(error_msg)
            return

        if response_data["order_type"] == "limit" and response_data["limit_price"] is None:
            error_msg = "Please provide a valid limit price for limit orders."
            await send_json_to_websocket(phonenumber, {
                "type": "log",
                "type_of_data": "text",
                "query_type": "trade_response",
                "data": {**response_data, "error": error_msg},
                "all_data": get_order_book_status(user_id, db)
            })
            await params.result_callback(error_msg)
            return

        if response_data["action"] not in ["buy", "sell"]:
            error_msg = "Please provide a valid action (buy or sell)."
            await send_json_to_websocket(phonenumber, {
                "type": "log",
                "type_of_data": "text",
                "query_type": "trade_response",
                "data": {**response_data, "error": error_msg},
                "all_data": get_order_book_status(user_id, db)
            })
            await params.result_callback(error_msg)
            return

        # Get the asset_id for the given symbol
        asset = db.query(AssetType).filter(AssetType.asset_ticker == response_data["symbol"]).first()
        if not asset:
            error_msg = f"Asset with symbol {response_data['symbol']} not found."
            await send_json_to_websocket(phonenumber, {
                "type": "log",
                "type_of_data": "text",
                "query_type": "trade_response",
                "data": {**response_data, "error": error_msg},
                "all_data": get_order_book_status(user_id, db)
            })
            await params.result_callback(error_msg)
            return

        # Get the real-time price from yfinance
        current_price = get_realtime_stock_price(response_data['symbol'])

        if not current_price:
            error_msg = f"Unable to fetch current price for {response_data['symbol']}. Please try again."
            logger.bind(frontend=True).error(f"Trade failed: {error_msg}")
            await send_json_to_websocket(phonenumber, {
                "type": "log",
                "type_of_data": "text",
                "query_type": "trade_response",
                "data": {**response_data, "error": error_msg},
                "all_data": get_order_book_status(user_id, db)
            })
            await params.result_callback(error_msg)
            return

        response_data['unit_price'] = round(current_price, 2)

        # Calculate the amount
        amount = round(float(response_data["quantity"]) * (float(response_data["limit_price"]) if response_data["limit_price"] else current_price), 2)
        response_data['amount'] = amount

        # Create a new order
        new_order = OrderBook(
            user_id=user_id,
            asset_id=asset.asset_id,
            order_type="Limit" if response_data["order_type"] == "limit" else "Market",
            symbol=response_data["symbol"],
            description=f"{response_data['action'].capitalize()} {response_data['quantity']} units of {response_data['symbol']}",
            buy_sell=response_data['action'].capitalize(),
            unit_price=round(current_price, 2),
            limit_price=float(response_data["limit_price"]) if response_data["order_type"] == "limit" else None,
            qty=float(response_data["quantity"]),
            amount=amount,
            settlement_date=date.today(),  # You might want to adjust this based on your business logic
            order_status="Under Review",
            order_date=datetime.now(),
        )
        response_data['order_date'] = new_order.order_date.strftime("%Y-%m-%d %H:%M:%S")
        response_data['order_status'] = new_order.order_status

        # Add the new order to the database
        db.add(new_order)
        db.commit()

        if amount > cash_balance and response_data["action"] == "buy":
            error_msg = f"Insufficient cash balance to place the trade. Your cash balance is {cash_balance}, but the required amount is {amount}."
            await send_json_to_websocket(phonenumber, {
                "type": "log",
                "type_of_data": "text",
                "query_type": "trade_response",
                "data": {**response_data, "error": error_msg},
                "all_data": get_order_book_status(user_id, db)
            })
            await params.result_callback(error_msg)
            return

        # Send the trade response
        await send_json_to_websocket(phonenumber, {
            "type": "log",
            "type_of_data": "text",
            "query_type": "trade_response",
            "data": response_data,
            "all_data": get_order_book_status(user_id, db)
        })

        # Return success response  
        success_msg = f"Trade under review: {response_data['action']} {response_data['quantity']} units of {response_data['symbol']}. Ask user to confirm the trade or whether any update is required"  
        await params.result_callback(success_msg)

    except Exception as e:
        db.rollback()
        logger.error(f"Error placing trade: {e}")
        error_msg = f"Sorry, I encountered an error while placing your trade: {str(e)}"
        await send_json_to_websocket(phonenumber, {
            "type": "log",
            "type_of_data": "text",
            "query_type": "trade_response",
            "data": {**response_data, "error": error_msg},
            "all_data": get_order_book_status(user_id, db)
        })
        await params.result_callback(error_msg)
        raise CustomException(error_message="Failed to place trade", error_details=sys.exc_info())
    finally:
        db.close()

async def update_trade(params: FunctionCallParams):  
    db = SessionLocal()  
    try:  
        # Extract parameters  
        order_id = params.arguments.get("order_id")  
        user_id = params.arguments.get("user_id")  
        symbol = params.arguments.get("symbol")  
        quantity = params.arguments.get("quantity")  
        order_type = params.arguments.get("order_type")  
        limit_price = params.arguments.get("limit_price")  
        action = params.arguments.get("action")  

        phonenumber = db.query(User.phone_number).filter(User.user_id == user_id).scalar()
        #get the cash balance of the user using centralized function
        cash_balance = calculate_available_cash_balance(user_id, db)

        if action == "buy":
            if order_id is None:
                order = db.query(OrderBook).filter(OrderBook.order_status == "Under Review", OrderBook.user_id == user_id).order_by(OrderBook.order_date.desc()).first()  
            else:
                # Fetch the order  
                order = db.query(OrderBook).filter(OrderBook.order_id == order_id, OrderBook.order_status == "Under Review").first()  
            if not order:  
                raise ValueError("Trade order not found or is not in under review state.") 
        if action == "sell":
            if order_id is None:
                order = db.query(OrderBook).filter(OrderBook.order_status == "Under Review", OrderBook.user_id == user_id).order_by(OrderBook.order_date.desc()).first()  
            else:
                # Fetch the order
                order = db.query(OrderBook).filter(OrderBook.order_id == order_id, OrderBook.order_status == "Placed").first()
            if not order:
                raise ValueError("Trade order not found or is not in placed state.")     
  
        # Update fields if provided  
        if user_id:  
            order.user_id = user_id  
        if symbol:  
            # Validate the new symbol  
            asset = db.query(AssetType).filter(AssetType.asset_ticker == symbol).first()  
            if not asset:  
                raise ValueError(f"Asset with symbol {symbol} not found.")  
            order.symbol = symbol  
            order.asset_id = asset.asset_id  # Update associated asset_id  
        if quantity:  
            if int(quantity) <= 0:  
                raise ValueError("Quantity must be greater than zero.")  
            order.qty = quantity  
        if order_type:  
            if order_type not in ["market", "limit"]:  
                raise ValueError("Invalid order type. Must be 'market' or 'limit'.")  
            order.order_type = order_type.capitalize()  
        if limit_price:  
            if order_type == "limit" and float(limit_price) <= 0:  
                raise ValueError("Limit price must be greater than zero.")  
            order.limit_price = limit_price  
        if action:  
            if action not in ["buy", "sell"]:  
                raise ValueError("Invalid action. Must be 'buy' or 'sell'.")  
            order.buy_sell = action.capitalize()  

        # Get the real-time price from yfinance
        current_price = get_realtime_stock_price(order.symbol)

        if not current_price:
            raise ValueError(f"Unable to fetch current price for {order.symbol}. Please try again.")

        # Recalculate the amount
        if quantity or limit_price:
            updated_price = float(limit_price) if limit_price else current_price
            updated_quantity = float(quantity) if quantity else order.qty
            order.amount = round(updated_quantity * updated_price, 2)  # update the amount based on the latest price and quantity
            order.unit_price = round(current_price, 2)  # update the unit price to the latest close price

        response_data = {
            "trade": "Stocks/ETFs/Mutual Fund",
            "account": "Brokerage Account",
            "symbol": order.symbol,
            "action": order.buy_sell,
            "order_type": order.order_type,
            "quantity": order.qty,
            "unit_price": order.unit_price,
            "limit_price": order.limit_price,
            "amount": order.amount,
            "cash_balance": cash_balance,
            "order_date": order.order_date.strftime("%Y-%m-%d %H:%M:%S"),
            "order_status": order.order_status,
        }

        if cash_balance < order.amount and action == "buy":
            error_msg = f"Insufficient cash balance for buy order. Available: {cash_balance}, Required: {order.amount}"
            await send_json_to_websocket(phonenumber, {
                "type": "log",
                "type_of_data": "text",
                "query_type": "trade_response",
                "data": {**response_data, "error": error_msg},
                "all_data": get_order_book_status(user_id, db)
            })
            await params.result_callback(error_msg)
            return
        
        if action == "sell":            
            if order.order_type == "Market":  
                cash_balance += quantity * latest_price_record.close_price  
            else:  
                cash_balance += quantity * order.limit_price  

        # Commit changes to the database
        db.commit()

        #Send the trade response
        await send_json_to_websocket(phonenumber, {
            "type": "log",
            "type_of_data": "text",
            "query_type": "trade_response",
            "data": response_data,
            "all_data": get_order_book_status(user_id, db)
        })
  
        # Return success response  
        success_msg = f"Trade order {order_id} updated successfully. Ask confirmation from the user to place the order."  
        await params.result_callback(success_msg)  
  
    except Exception as e:  
        db.rollback()  
        error_msg = f"Failed to update trade order: {str(e)}"  
        await params.result_callback(error_msg)  
        raise CustomException(error_message="Failed to update trade order", error_details=sys.exc_info())
    finally:  
        db.close()   

async def confirm_trade(params: FunctionCallParams):  
    db = SessionLocal()  
    try:  
        order_id = params.arguments.get("order_id")  
        user_id = params.arguments.get("user_id")
        phonenumber = db.query(User.phone_number).filter(User.user_id == user_id).scalar()

        if order_id is None:  
            order = db.query(OrderBook).filter(OrderBook.order_status == "Under Review", OrderBook.user_id == user_id).order_by(OrderBook.order_date.desc()).first()
        
        else:
            # Fetch the order  
            order = db.query(OrderBook).filter(OrderBook.order_id == order_id, OrderBook.order_status == "Under Review").first()  
        if not order:
            raise ValueError("Trade order not found or is not in under review state.")

        # Get raw CASH balance to check if we can execute this specific order
        raw_cash_balance = db.query(UserPortfolio.investment_amount).join(AssetType, UserPortfolio.asset_id == AssetType.asset_id).filter(UserPortfolio.user_id == user_id,AssetType.asset_ticker=='CASH').scalar()

        if raw_cash_balance < order.amount and order.buy_sell == "Buy":
            error_msg = f"Insufficient cash balance to confirm the trade. Your cash balance is {raw_cash_balance}, but the required amount is {order.amount}."
            await send_json_to_websocket(phonenumber, {
                "type": "log",
                "type_of_data": "text",
                "query_type": "trade_response",
                "all_data" : get_order_book_status(user_id,db)
            })
            await params.result_callback(error_msg)
            return

        # Get available cash balance for display (subtracts ALL pending orders including this one)
        available_cash = calculate_available_cash_balance(user_id, db)

        response_data = {
            "trade": "Stocks/ETFs/Mutual Fund",
            "account": "Brokerage Account",
            "symbol": order.symbol,
            "action": order.buy_sell,
            "order_type": order.order_type,
            "quantity": order.qty,
            "unit_price": order.unit_price,
            "limit_price": order.limit_price,
            "amount": order.amount,
            "cash_balance": available_cash,  # Use centralized calculation
            "order_date": order.order_date.strftime("%Y-%m-%d %H:%M:%S"),
            "order_status": order.order_status,
        }
        
        if order.buy_sell == "Buy":
            # Verify we have enough available cash (this check is redundant but kept for safety)
            if available_cash < 0:
                error_msg = f"Insufficient available cash to confirm the trade. Available cash: ${available_cash:.2f}, Required: ${order.amount:.2f}"
                await send_json_to_websocket(phonenumber, {
                    "type": "log",
                    "type_of_data": "text",
                    "query_type": "trade_response",
                    "data": {**response_data, "error": error_msg},
                    "all_data" : get_order_book_status(user_id,db)
                })
                await params.result_callback(error_msg)
                return

        if order.buy_sell == "Sell":
            asset_total_qty = db.query(UserPortfolio.asset_total_units).join(AssetType, UserPortfolio.asset_id == AssetType.asset_id).filter(UserPortfolio.user_id == user_id, AssetType.asset_ticker == order.symbol).scalar()
            # Only check against other "Under Review" sell orders since "Placed" orders are already executed
            total_qty = max(0, asset_total_qty - (
                        db.query(func.sum(OrderBook.qty))
                        .filter(
                            OrderBook.user_id == user_id,
                            OrderBook.asset_id == order.asset_id,
                            OrderBook.order_status == "Under Review",
                            OrderBook.buy_sell == "Sell"
                        )
                        .scalar() or 0
                    ))
            print("Total quantity after sell action:", total_qty)
            if order.qty > total_qty:
                error_msg = f"Invalid quantity for sell action. Quantity cannot be more than the available quantity for the symbol {order.symbol}."
                await send_json_to_websocket(phonenumber, {
                    "type": "log",
                    "type_of_data": "text",
                    "query_type": "trade_response",
                    "data": {**response_data, "error": error_msg},
                    "all_data" : get_order_book_status(user_id,db)
                })
                await params.result_callback(error_msg)
                return

        # Execute the trade by updating UserPortfolio
        cash_asset_id = db.query(AssetType.asset_id).filter(AssetType.asset_ticker == 'CASH').scalar()

        if order.buy_sell == "Buy":
            # Deduct cash from user's cash balance
            cash_portfolio = db.query(UserPortfolio).filter(
                UserPortfolio.user_id == user_id,
                UserPortfolio.asset_id == cash_asset_id
            ).first()

            if cash_portfolio:
                cash_portfolio.investment_amount -= order.amount
                cash_portfolio.asset_total_units -= order.amount

            # Add or update the purchased asset in portfolio
            asset_portfolio = db.query(UserPortfolio).filter(
                UserPortfolio.user_id == user_id,
                UserPortfolio.asset_id == order.asset_id
            ).first()

            if asset_portfolio:
                # Update existing asset
                total_cost = asset_portfolio.investment_amount + order.amount
                total_units = asset_portfolio.asset_total_units + order.qty
                asset_portfolio.avg_cost_per_unit = total_cost / total_units if total_units > 0 else 0
                asset_portfolio.asset_total_units = total_units
                asset_portfolio.investment_amount = total_cost
            else:
                # Create new asset entry
                new_portfolio = UserPortfolio(
                    user_id=user_id,
                    asset_id=order.asset_id,
                    asset_total_units=order.qty,
                    avg_cost_per_unit=order.unit_price,
                    investment_amount=order.amount
                )
                db.add(new_portfolio)

            # Create transaction record
            new_transaction = UserTransactions(
                user_id=user_id,
                asset_id=order.asset_id,
                trans_type="Buy",
                date=date.today(),
                units=order.qty,
                price_per_unit=order.unit_price,
                cost=order.amount
            )
            db.add(new_transaction)

        elif order.buy_sell == "Sell":
            # Add cash to user's cash balance
            cash_portfolio = db.query(UserPortfolio).filter(
                UserPortfolio.user_id == user_id,
                UserPortfolio.asset_id == cash_asset_id
            ).first()

            if cash_portfolio:
                cash_portfolio.investment_amount += order.amount
                cash_portfolio.asset_total_units += order.amount

            # Reduce the sold asset in portfolio
            asset_portfolio = db.query(UserPortfolio).filter(
                UserPortfolio.user_id == user_id,
                UserPortfolio.asset_id == order.asset_id
            ).first()

            if asset_portfolio:
                asset_portfolio.asset_total_units -= order.qty
                asset_portfolio.investment_amount -= (asset_portfolio.avg_cost_per_unit * order.qty)

                # If all units are sold, we can optionally remove the entry or keep it at 0
                if asset_portfolio.asset_total_units <= 0:
                    asset_portfolio.asset_total_units = 0
                    asset_portfolio.investment_amount = 0

            # Create transaction record
            new_transaction = UserTransactions(
                user_id=user_id,
                asset_id=order.asset_id,
                trans_type="Sell",
                date=date.today(),
                units=order.qty,
                price_per_unit=order.unit_price,
                cost=order.amount
            )
            db.add(new_transaction)

        # Update order status to Placed (Executed)
        order.order_status = "Placed"
        response_data["order_status"] = order.order_status

        # Commit all changes
        db.commit()

        # Get updated cash balance after execution using centralized function
        updated_cash_balance = calculate_available_cash_balance(user_id, db)
        response_data["cash_balance"] = updated_cash_balance

        await send_json_to_websocket(phonenumber, {
            "type": "log",
            "type_of_data": "text",
            "query_type": "trade_response",
            "data": response_data,
            "all_data" : get_order_book_status(user_id,db)
        })

        # Return success response
        success_msg = f"Trade order executed successfully. Updated cash balance: ${updated_cash_balance:.2f}"
        await params.result_callback(success_msg)
  
    except Exception as e:  
        db.rollback()  
        error_msg = f"Failed to confirm trade order: {str(e)}"  
        await params.result_callback(error_msg)  
        raise  CustomException(error_message="Failed to confirm trade order", error_details=sys.exc_info())
    finally:  
        db.close()  

async def check_order_status(params: FunctionCallParams):
    # Implement the logic to check an order's status
    db = SessionLocal()
    try:
        order_id = params.arguments.get("order_id")
        user_id = params.arguments.get("user_id")

        if not order_id:
            order = db.query(OrderBook).filter(OrderBook.user_id == user_id).order_by(OrderBook.order_date.desc()).first()

        else:
            # Fetch the order
            order = db.query(OrderBook).filter(OrderBook.order_id == order_id, OrderBook.user_id == user_id).first()

        if not order:
            await params.result_callback(f"No order found with ID {order_id} for user {user_id}.")
            return

        response_data = {
            "order_id": order.order_id,
            "status": order.order_status,
            "symbol": order.symbol,
            "action": order.buy_sell,
            "quantity": order.qty,
            "unit_price": order.unit_price,
            "limit_price": order.limit_price,
            "amount": order.amount,
            "order_date": order.order_date.strftime("%Y-%m-%d %H:%M:%S"),
        }

        phonenumber = db.query(User.phone_number).filter(User.user_id == user_id).scalar()
        await send_json_to_websocket(phonenumber, {
            "type": "log",
            "type_of_data": "text",
            "query_type": "trade_response",
            "data": response_data,
            "all_data": get_order_book_status(user_id, db)
        })

        await params.result_callback(f"Order status for ID {order.order_id}: {order.order_status}")

    except Exception as e:
        logger.error(f"Error checking order status: {str(e)}")
        await params.result_callback(f"Sorry, I encountered an error while checking the order status: {str(e)}")
        raise CustomException(error_message="Failed to check order status", error_details=sys.exc_info())
    finally:
        db.close()

async def cancel_order(params: FunctionCallParams):
    # Implement the logic to cancel an order
    db = SessionLocal()
    try:
        order_id = params.arguments.get("order_id")
        user_id = params.arguments.get("user_id")

        if not order_id:
            order = db.query(OrderBook).filter(OrderBook.user_id == user_id, OrderBook.order_status == "Under Review").order_by(OrderBook.order_date.desc()).first()

        else:
            # Fetch the order
            order = db.query(OrderBook).filter(OrderBook.order_id == order_id, OrderBook.user_id == user_id).first()

        if not order:
            await params.result_callback(f"No under review order found with ID {order_id} for user {user_id}.")
            return

        # Update the order status to "Cancelled"
        order.order_status = "Cancelled"
        db.commit()

        response_data = {
            "order_id": order.order_id,
            "status": order.order_status,
            "symbol": order.symbol,
            "action": order.buy_sell,
            "quantity": order.qty,
            "unit_price": order.unit_price,
            "limit_price": order.limit_price,
            "amount": order.amount,
            "order_date": order.order_date.strftime("%Y-%m-%d %H:%M:%S"),
        }

        phonenumber = db.query(User.phone_number).filter(User.user_id == user_id).scalar()
        await send_json_to_websocket(phonenumber, {
            "type": "log",
            "type_of_data": "text",
            "query_type": "trade_response",
            "data": response_data,
            "all_data": get_order_book_status(user_id, db)
        })

        await params.result_callback(f"Order with ID {order.order_id} has been cancelled.")
    except Exception as e:
       logger.error(f"Error cancelling order: {str(e)}")
       await params.result_callback(f"Sorry, I encountered an error while cancelling the order: {str(e)}")
       raise CustomException(error_message="Failed to cancel order", error_details=sys.exc_info())    
    finally:
       db.close()

async def update_cash_balance(params: FunctionCallParams):

    db = SessionLocal()
    try:
        user_id = params.arguments.get("user_id")
        amount = params.arguments.get("amount")
        action = params.arguments.get("action")  # "add" or "subtract"

        if amount is None or amount < 0:
            await params.result_callback("Please provide a valid cash balance.")
            return

        cash_asset_id = db.query(AssetType.asset_id).filter(AssetType.asset_ticker == 'CASH').scalar()
        # Update the user's cash balance
        user_portfolio = db.query(UserPortfolio).filter(UserPortfolio.user_id == user_id, UserPortfolio.asset_id == cash_asset_id).first()
        if not user_portfolio:
            await params.result_callback("User portfolio not found.")
            return

        if action == "add":
            user_portfolio.investment_amount += amount
            user_portfolio.asset_total_units += amount  # Assuming this is the cash asset
        elif action == "subtract":
            user_portfolio.investment_amount -= amount
            user_portfolio.asset_total_units -= amount

        db.commit()
        phonenumber = db.query(User.phone_number).filter(User.user_id == user_id).scalar()

        result = get_portfolio_summary(user_id=user_id)
        
        await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"table","query_type":"user_portfolio","data": result})
        
        await params.result_callback(f"Cash balance updated to {user_portfolio.investment_amount}.")
    except Exception as e:
        logger.error(f"Error updating cash balance: {str(e)}")
        await params.result_callback(f"Sorry, I encountered an error while updating the cash balance: {str(e)}")
        raise CustomException(error_message="Failed to update cash balance", error_details=sys.exc_info())
    finally:
        db.close()

async def get_bank_accounts(params: FunctionCallParams):
    db = SessionLocal()
    try:
        user_id = params.arguments.get("user_id")

        bank_accounts = db.query(UserBankAccount).filter(
            UserBankAccount.user_id == user_id,
            UserBankAccount.is_active == 1
        ).all()

        if not bank_accounts:
            await params.result_callback("You don't have any bank accounts linked. Please contact support to add a bank account.")
            return

        accounts_info = []
        for account in bank_accounts:
            accounts_info.append(
                f"{account.bank_name} {account.account_type} ending in {account.account_number} "
                f"with available balance of ${account.available_balance:,.2f}"
            )

        phonenumber = db.query(User.phone_number).filter(User.user_id == user_id).scalar()

        accounts_data = {
            "bank_accounts": [
                {
                    "bank_account_id": acc.bank_account_id,
                    "bank_name": acc.bank_name,
                    "account_number": acc.account_number,
                    "account_type": acc.account_type,
                    "available_balance": round(acc.available_balance, 2)
                }
                for acc in bank_accounts
            ]
        }

        await send_json_to_websocket(phonenumber, {
            "type": "log",
            "type_of_data": "table",
            "query_type": "bank_accounts",
            "data": accounts_data
        })

        result_message = f"You have {len(bank_accounts)} bank account(s):\n" + "\n".join(accounts_info)
        await params.result_callback(result_message)

    except Exception as e:
        logger.error(f"Error retrieving bank accounts: {str(e)}")
        await params.result_callback(f"Sorry, I encountered an error while retrieving your bank accounts: {str(e)}")
        raise CustomException(error_message="Failed to retrieve bank accounts", error_details=sys.exc_info())
    finally:
        db.close()

async def transfer_from_bank(params: FunctionCallParams):
    db = SessionLocal()
    try:
        user_id = params.arguments.get("user_id")
        bank_account_id = params.arguments.get("bank_account_id")
        amount = params.arguments.get("amount")

        if amount is None or amount <= 0:
            await params.result_callback("Please provide a valid transfer amount greater than zero.")
            return

        # Get the bank account
        bank_account = db.query(UserBankAccount).filter(
            UserBankAccount.bank_account_id == bank_account_id,
            UserBankAccount.user_id == user_id,
            UserBankAccount.is_active == 1
        ).first()

        if not bank_account:
            await params.result_callback("Bank account not found. Please verify the account ID.")
            return

        # Check if bank has sufficient balance
        if bank_account.available_balance < amount:
            await params.result_callback(
                f"Insufficient funds in your {bank_account.bank_name} account. "
                f"Available balance is ${bank_account.available_balance:,.2f}, but you're trying to transfer ${amount:,.2f}."
            )
            return

        # Get the cash asset
        cash_asset_id = db.query(AssetType.asset_id).filter(AssetType.asset_ticker == 'CASH').scalar()
        if not cash_asset_id:
            await params.result_callback("Cash asset not found in system.")
            return

        # Get or create user's cash portfolio entry
        user_cash_portfolio = db.query(UserPortfolio).filter(
            UserPortfolio.user_id == user_id,
            UserPortfolio.asset_id == cash_asset_id
        ).first()

        if not user_cash_portfolio:
            # Create new cash portfolio entry
            user_cash_portfolio = UserPortfolio(
                user_id=user_id,
                asset_id=cash_asset_id,
                asset_total_units=amount,
                avg_cost_per_unit=1.0,
                investment_amount=amount
            )
            db.add(user_cash_portfolio)
        else:
            # Update existing cash portfolio
            user_cash_portfolio.investment_amount += amount
            user_cash_portfolio.asset_total_units += amount

        # Deduct from bank account
        bank_account.available_balance -= amount

        # Commit the transaction
        db.commit()

        phonenumber = db.query(User.phone_number).filter(User.user_id == user_id).scalar()

        # Send updated portfolio
        result = get_portfolio_summary(user_id=user_id)
        await send_json_to_websocket(phonenumber, {
            "type": "log",
            "type_of_data": "table",
            "query_type": "user_portfolio",
            "data": result
        })

        result_message = (
            f"Successfully transferred ${amount:,.2f} from your {bank_account.bank_name} "
            f"{bank_account.account_type} to your brokerage account. "
            f"Your new brokerage cash balance is ${user_cash_portfolio.investment_amount:,.2f}."
        )
        await params.result_callback(result_message)

    except Exception as e:
        db.rollback()
        logger.error(f"Error transferring funds: {str(e)}")
        await params.result_callback(f"Sorry, I encountered an error while transferring funds: {str(e)}")
        raise CustomException(error_message="Failed to transfer funds", error_details=sys.exc_info())
    finally:
        db.close()

async def get_price_trend(params: FunctionCallParams):
    session = SessionLocal()

    try:
        user_id = params.arguments["user_id"]
        time_history = params.arguments.get("time_history", 2)  # Default to 2 years if not provided
        ticker_value = params.arguments.get("ticker_value", [])

        if time_history not in [1, 2, 3, 5]:
            await params.result_callback(f"Invalid time history value: {time_history}. Please select from 1, 2, 3, or 5 years.")
            return
        if time_history == 1:
            interval = "monthly"
        elif time_history > 1:
            interval = "quarterly"

        if not all(item in PortfolioToolSchemas.get_dynamic_ticker_values() for item in ticker_value):
           await params.result_callback(f"Invalid ticker value: {ticker_value}. Please select from the available options.")
           return

        phonenumber = session.query(User.phone_number).filter(User.user_id == user_id).scalar()    

        extended_data = AssetHistory.get_extended_data(session, user_id)
            
        # Convert to DataFrame
        df = pd.DataFrame(extended_data, columns=[
            'asset_hist_id', 'asset_id', 'date', 'close_price', 'asset_class','asset_name', 'concentration',
            'asset_manager', 'category', 'ticker', 'sector', 'sector_weightage', 'asset_total_units'
        ])
        df = df[df['ticker'].isin(ticker_value)]  # Filter by the selected ticker value
        # Ensure 'date' is in datetime format
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year

        df['sector_weightage'] = df['sector_weightage'].fillna(100)  # Fill NaN with 100 for sector weightage
        df = df.drop_duplicates(subset=['asset_hist_id'], keep='last')
        df['portfolio'] = df['close_price'] * df['asset_total_units'] * df['sector_weightage']/100   
        
        ################################# For daily returns line chart ########################
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        date_mark = df['date'].max() - timedelta(days=365 * time_history)

        portfolio_data = df[df['date'] >= date_mark]
        portfolio_data = portfolio_data.sort_values(by=['date'], ascending=False)
        portfolio_data = portfolio_data[['date', 'ticker', 'portfolio', 'close_price']].copy()
        # portfolio_data = portfolio_data.groupby(['date','ticker']).agg({'portfolio': 'sum'}).reset_index()

        # portfolio_data = calculate_line_chart_return(portfolio_data).reset_index(drop=True)

        # portfolio_data['portfolio_return'] = round(portfolio_data['portfolio_return'],2)

        portfolio_data = portfolio_data.rename(columns={'ticker': 'dimension','close_price': 'portfolio_return'}) #forcefully changing the close_price column name to match the portfolio_benchmark chart generation function

        portfolio_data = portfolio_data[['date','dimension','portfolio','portfolio_return']]
        # Convert 'date' column to datetime if it's not already
        portfolio_data['date'] = pd.to_datetime(portfolio_data['date'])

        # Extract just the date part (removing the time)
        portfolio_data['date'] = portfolio_data['date'].dt.date
        ############################# Line Chart End ##########################

        # Set date as index
        df.set_index('date', inplace=True)
    
        all_data = []

        for ele in ticker_value:
            asset_data = df[df['ticker'] == ele]
            if not asset_data.empty:
                all_data.append(process_time_period_data(asset_data,["ticker"], interval,time_history))

        # all_data.append(process_time_period_data(df, ["ticker"], interval, time_history))
        all_data = pd.DataFrame(pd.concat(all_data, ignore_index=True))

        all_data = all_data.sort_values(['year', 'freq', 'index_name'], ascending=[False, False, True]).reset_index(drop=True)
        # all_data.to_excel("check_all_data.xlsx", index=False)
        # Calculate returns for each index
        all_data['return'] = all_data.groupby('index_name')['close_price'].pct_change(-1) * 100
        all_data['return'] = round(all_data['return'],2)
        #remove the last row
        all_data = all_data[:-1]
        # all_data.to_excel("check_all_data2.xlsx", index=False)
        # Format close price
        all_data['close_price'] = round(all_data['close_price'],2)

        # Reorder columns
        columns = ['year', 'freq', 'last_date', 'index_name', 'close_price', 'return']
        all_data = all_data[columns]
        all_data = all_data.rename(columns={'index_name': 'dimension','date':'last_date','close_price': 'portfolio','return': 'portfolio_return'})
        all_data = all_data.dropna()

        result = all_data.copy()
        final_line_chart_df = portfolio_data.copy()

        result['last_date'] = result['last_date'].dt.strftime('%Y-%m-%d')

        result['portfolio'] = round(result['portfolio'],2)

        # result = pd.merge(result, index_return_df, on='last_date', how='inner')

        # Convert 'quarter' to string format
        result['freq'] = result['freq'].astype(str)
        result = result.drop(columns=['date_marker'], errors='ignore')
        result = result.dropna()

        # Format the results
        formatted_results = result.to_dict('records')     

        chart_data = performance_chart(result,final_line_chart_df,time_history,interval,title=f"Price Trend Analysis - {time_history}yr",y_axis_display_name="Price")

        chart_data = json.loads(chart_data)

        await send_json_to_websocket(phonenumber, chart_data)
        # logger.bind(frontend=True).bind(log_type="Json").bind(log_type_of_data="chart").success(json.dumps(result)) 

        formatted_results_json = json.dumps(formatted_results)

        # The rest of your code remains the same
        result = {
            'data': json.loads(formatted_results_json)
        }

        
        result_json = json.dumps(result)

        # await send_json_to_websocket(phonenumber, {"type":"log","type_of_data":"chart","query_type":"performance","data": json.loads(result_json)})
        # logger.bind(frontend=True).success(json.loads(result_json))
        await params.result_callback(f"Your results are ready and on your screen. Results: {json.loads(result_json)}. Do not read out the result and use only for the context of the call")
    except Exception as e:
        logger.error(f"An error occurred while processing price trend analysis: {e}")
        await params.result_callback(f"An error occurred while processing your request: {str(e)}")
        raise CustomException(error_message="Failed to process price trend analysis", error_details=sys)
    finally:
        session.close()        