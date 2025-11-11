from typing import List
from pipecat.adapters.schemas.function_schema import FunctionSchema
from sqlalchemy import distinct
from src.database.models import *
from src.database.database import SessionLocal
from contextlib import closing

class PortfolioToolSchemas:
    @staticmethod
    def get_dimension_levels() -> List[str]:
        return [
            "Security", "Instrument", "Underlying", "Holding", "Ticker", "Holdings", "Asset Ticker",
            "Market Segment", "Vertical", "Sector",
            "Investment Category", "Security Class", "Investment Vehicle", "Asset Type", "Asset Class",
            "Asset Manager", "Investment House", "Investment Family", "Fund Group", "Fund Family",
            "Concentration", "Category"
        ]

    @staticmethod
    def get_filter_values() -> List[str]:
        with closing(SessionLocal()) as db:
            queries = [
                db.query(distinct(AssetType.asset_class)),
                db.query(distinct(AssetType.concentration)),
                db.query(distinct(AssetSector.sector_name)),
                db.query(distinct(AssetType.asset_name)),
                db.query(distinct(AssetType.asset_ticker))
            ]
            
            results = [query.all() for query in queries]

        return [
            item[0] for sublist in results
            for item in sublist
            if item[0] is not None
        ]

    @staticmethod
    def get_dynamic_ticker_values() -> List[str]:
        # This should be replaced with a database call in a real implementation
        #get it from the database
        db = SessionLocal()
        try:
            # Get the unique list of tickers from database
            tickers = db.query(distinct(AssetType.asset_ticker)).filter(AssetType.asset_ticker.isnot(None)).all()
            return [ticker[0] for ticker in tickers]
        finally:
            db.close()

    @classmethod
    def authenticate_user_tool(cls):
        return FunctionSchema(
            name="authenticate_user_tool",
            description="Use this tool to authenticate the user with the phone number and date of birth which user can say in any format but convert it into YYYY-MM-DD in the system",
            properties={
                "phonenumber": {
                    "type": "string",
                    "description": "the phone number of the user to authenticate shared during the beginning of the call",
                },
                "date_of_birth": {
                    "type": "string",
                    "description": "the date of birth of the user to authenticate shared during the call by the user convert it into format YYYY-MM-DD",
                },
            },
            required=["phonenumber"]
        )

    @classmethod
    def user_holding_tool(cls):
        return FunctionSchema(
            name="user_holding_tool",
            description="Use this tool to show the holding table of the user only when asked by the user.",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the user which is obtained after authenticating user.",
                },
            },
            required=["user_id"]
        )

    @classmethod
    def aggregation_tool(cls):
        return FunctionSchema(
            name="aggregation_tool",
            description="Get the answer for various portfolio distribution/breakdown related queries",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the user which is obtained after authenticating user.",
                },
                "aggregation_metric": {
                    "type": "string",
                    "description": "The metric to aggregate by. Can be 'total portfolio value' or 'percentage returns' which is same as portfolio performance",
                    "enum": ["total portfolio value", "percentage returns"]
                },
                "dimension_levels": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": cls.get_dimension_levels(),
                        "description": "The dimension to aggregate by. Refer to the Synonym Dictionary for alternative terms"
                    },
                    "description": "List of dimensions to aggregate by",
                },
                "filter_values": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": cls.get_filter_values()
                    },
                    "description": "Values for asset_class and sector",
                },
                "visualization_types": {
                    "type": "string",
                    "enum": ["donut", "bar"],
                    "description": "Type of visualization to use. Default is donut",
                    "default": "donut"
                },
            },
            required=["user_id", "aggregation_metric", "dimension_levels", "visualization_types"]
        )

    @classmethod
    def portfolio_benchmark_tool(cls):
        return FunctionSchema(
            name="portfolio_benchmark_tool",
            description="Get the portfolio benchmark for a user",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the user which is obtained after authenticating user",
                },
                "time_history": {
                    "type": "integer",
                    "description": "The time history in years to retrieve portfolio benchmark for",
                    "default": 2,
                },
                "dimension_levels": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": cls.get_dimension_levels(),
                        "description": "The dimension to aggregate by. Refer to the Synonym Dictionary for alternative terms"
                    },
                    "description": "List of dimensions to aggregate by for portfolio benchmarking",
                    "default": "all"
                },
                "benchmark_against": {
                    "type": "array",
                    "items":{
                        "type": "string",
                        "enum": ["SPX", "VTSAX", "VBTLX"]
                    },
                    "description": "This is the benchmark index which will be compared with the portfolio. Default is S&P 500",
                    "default": "S&P 500"
                },
                "filter_values": {
                    "type": "array",
                    "items":{
                        "type": "string",
                        "enum": cls.get_filter_values()
                    },
                    "description": "The specific asset for which the benchmark is to be retrieved",
                    "default": "all"
                },
                "interval": {
                    "type": "string",
                    "enum": ["weekly", "monthly", "quarterly", "yearly"],
                    "description": "The interval at which the benchmark is to be retrieved. Default is quarterly",
                },
            },
            required=["user_id", "time_history", "dimension_levels", "benchmark_against", "benchmark_for","interval"]
        )

    @classmethod
    def relative_performance_tool(cls):
        return FunctionSchema(
            name="relative_performance_tool",
            description="Get the relative portfolio performance for a user",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the user which is obtained after authenticating user to get the various sector distribution",
                },
                "time_history": {
                    "type": "string",
                    "enum": ["week","month","3month","6month","1year", "2year", "3year", "5year"],
                    "description": "The time period in years to retrieve portfolio relative performance.",
                    "default": "1year",
                },
                "filter_values": {
                    "type": "array",
                    "items": {                   
                        "type": "string",
                        "enum": cls.get_filter_values()
                    },
                    "description": "Values for asset_class and sector",
                },
            },
            required=["user_id", "time_history"]
        )

    @classmethod
    def risk_score_tool(cls):
        return FunctionSchema(
            name="risk_score_tool",
            description="Get the risk score of the user's portfolio",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the user after authentication",
                },
                "dimension_levels": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": cls.get_dimension_levels(),
                        "description": "The dimension to aggregate by"
                    },
                    "description": "List of dimensions to aggregate by for risk score"
                },
                "filter_values": {
                    "type": "array",
                    "items": {                   
                        "type": "string",
                        "enum": cls.get_filter_values()
                    },
                    "description": "The values to filter the risk score",
                }
            },
            required=["user_id"]
        )

    @classmethod
    def attribution_returns_tool(cls):
        return FunctionSchema(
            name="attribution_returns_tool",
            description="Get the attribution returns for a user portfolio",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the user which is obtained after authenticating user",
                },
                "time_history": {
                    "type": "string",
                    "enum": ["1month", "3months", "6months", "1year", "2years", "3years", "5years"],
                    "description": "The time history in years to retrieve attribution returns for",
                    "default": "1year",
                },
                "dimension_levels": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": cls.get_dimension_levels(),
                        "description": "The dimension to aggregate by. Refer to the Synonym Dictionary for alternative terms"
                    },
                    "description": "List of dimensions to aggregate by for attribution returns",
                    "default": "asset_class"
                },
                "filter_values": {
                    "type": "array",
                    "items": {                   
                        "type": "string",
                        "enum": cls.get_filter_values()
                    },
                    "description": "Values for asset_class and sector",
                },
            },
            required=["user_id", "time_history", "dimension_levels"]
        )

    @classmethod
    def news_tool(cls):
        return FunctionSchema(
            name="news_tool",
            description="Get the latest news on a topic by searching the web",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the user which is obtained after authenticating user",
                },
                "ticker": {
                    "type": "string",
                    "enum": cls.get_dynamic_ticker_values(),
                    "description": "send the ticker of the asset for which user want to get the news",
                    "default": None
                }
            },
            required=["ticker", "user_id"]
        )

    @classmethod
    def fund_fact_sheet_download_tool(cls):
        return FunctionSchema(
            name="fund_fact_sheet_download_tool",
            description="Get the fund fact sheet link for the given ticker",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the user which is obtained after authenticating user",
                },
                "ticker": {
                    "type": "string",
                    "enum": cls.get_dynamic_ticker_values(),
                    "description": "send the ticker of the asset for which user want to get the news",
                    "default": None
                }
            },
            required=["ticker", "user_id"]
        )

    @classmethod
    def fund_fact_sheet_query_tool(cls):
        return FunctionSchema(
            name="fund_fact_sheet_query_tool",
            description="Get the Answer for general queries related only to fund fact sheet of the fund.",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the user which is obtained after authenticating user",
                },
                "query": {
                    "type": "string",
                    "description": "Actual Query of the user without modification which needs to be answered",
                },
                "ticker": {
                    "type": "string",
                    "enum": cls.get_dynamic_ticker_values(),
                    "description": "send the ticker of the asset for which user want to query",
                    "default": None
                }

            },
            required=["query", "user_id","ticker"],
        )
    
    @classmethod
    def place_trade_tool(cls):
        return FunctionSchema(
            name="place_trade_tool",
            description="Use this tool to place a trade order for the user",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the authenticated user",
                },
                "symbol": {
                    "type": "string",
                    "description": "The stock symbol to trade",
                },
                "quantity": {
                    "type": "integer",
                    "description": "The number of shares to trade",
                },
                "order_type": {
                    "type": "string",
                    "enum": ["market", "limit"],
                    "description": "The type of order to place",
                },
                "limit_price": {
                    "type": "number",
                    "description": "The limit price for a limit order (optional for limit orders)",
                },
                "action": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Whether to buy or sell the stock",
                },
            },
            required=["user_id","symbol", "quantity", "order_type", "action"]
        )
    
    @classmethod
    def update_trade_tool(cls):  
        return FunctionSchema(  
            name="update_trade_tool",  
            description="Use this tool to update an existing trade order in the pending state. All parameters are optional.",  
            properties={  
                "order_id": {  
                    "type": "integer",  
                    "description": "The ID of the trade order to update (optional)",  
                },  
                "user_id": {  
                    "type": "string",  
                    "description": "The user_id of the authenticated user (optional)",  
                },  
                "symbol": {  
                    "type": "string",  
                    "description": "The stock symbol to trade (optional)",  
                },  
                "quantity": {  
                    "type": "integer",  
                    "description": "The updated number of shares to trade (optional)",  
                },  
                "order_type": {  
                    "type": "string",  
                    "enum": ["market", "limit"],  
                    "description": "The updated type of order to place (optional)",  
                },  
                "limit_price": {  
                    "type": "number",  
                    "description": "The updated limit price for the trade (optional for limit orders)",  
                },  
                "action": {  
                    "type": "string",  
                    "enum": ["buy", "sell"],  
                    "description": "The updated action (buy or sell) for the trade (optional)",  
                },  
            },  
            required=["user_id"]  
        )  

    @classmethod
    def confirm_trade_tool(cls):  
        return FunctionSchema(  
            name="confirm_trade_tool",  
            description="Use this tool to confirm a trade order and move it out of the pending state",  
            properties={  
                "user_id": {  
                    "type": "string",  
                    "description": "The user_id of the authenticated user",  
                },
                "order_id": {  
                    "type": "integer",  
                    "description": "The ID of the trade order to confirm (optional, if not provided, confirm the most recent order)",  
                },  
            },  
            required=["user_id"]  
        )  
    
    @classmethod
    def check_order_status_tool(cls):
        return FunctionSchema(
            name="check_order_status_tool",
            description="Use this tool to check the status of a placed order",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the authenticated user",
                },
                "order_id": {
                    "type": "string",
                    "description": "The ID of the order to check (optional, if not provided, check the most recent order)",
                },
            },
            required=["user_id"]
        )

    @classmethod
    def cancel_order_tool(cls):
        return FunctionSchema(
            name="cancel_order_tool",
            description="Use this tool to cancel an open order",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the authenticated user",
                },
                "order_id": {
                    "type": "string",
                    "description": "The ID of the order to cancel (optional, if not provided, cancel the most recent order)",
                },
            },
            required=["user_id"]
        )
    
    @classmethod
    def update_cash_balance_tool(cls):
        return FunctionSchema(
            name="update_cash_balance_tool",
            description="Use this tool to update the cash balance of the user. Like transferring money from the bank account to the brokerage account or vice versa.",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the authenticated user",
                },
                "amount": {
                    "type": "number",
                    "description": "The amount to add or subtract from the cash balance",
                },
                "action": {
                    "type": "string",
                    "enum": ["add", "subtract"],
                    "description": "Whether to add or subtract the amount from the cash balance",
                },
            },
            required=["user_id", "amount", "action"]
            )

    @classmethod
    def get_bank_accounts_tool(cls):
        return FunctionSchema(
            name="get_bank_accounts_tool",
            description="Use this tool to retrieve and display the user's bank accounts with balances. When user wants to view their accounts verbally, set show_ui=false. When user needs to transfer funds, set show_ui=true to open the transfer interface.",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the authenticated user",
                },
                "show_ui": {
                    "type": "boolean",
                    "description": "Set to true to open the fund transfer UI interface. Set to false to provide verbal response of bank accounts. Default is false.",
                },
            },
            required=["user_id"]
        )

    @classmethod
    def transfer_from_bank_tool(cls):
        return FunctionSchema(
            name="transfer_from_bank_tool",
            description="Use this tool to transfer funds from a user's bank account to their brokerage account. The user can select from available bank accounts by name (e.g., 'Chase', 'Wells Fargo', 'Bank of America') or by ID and specify the transfer amount. Use this when the user wants to add funds to their brokerage account or when they have insufficient cash balance for a trade.",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the authenticated user",
                },
                "bank_account_id": {
                    "type": "number",
                    "description": "The ID of the bank account to transfer from. Either bank_account_id or bank_name must be provided.",
                },
                "bank_name": {
                    "type": "string",
                    "description": "The name of the bank to transfer from (e.g., 'Chase', 'Wells Fargo', 'Bank of America', 'BofA'). Supports partial names and fuzzy matching. Either bank_account_id or bank_name must be provided.",
                },
                "amount": {
                    "type": "number",
                    "description": "The amount to transfer from the bank account to the brokerage account (must be positive)",
                },
            },
            required=["user_id", "amount"]
        )

    @classmethod
    def dismiss_fund_transfer_tool(cls):
        return FunctionSchema(
            name="dismiss_fund_transfer_tool",
            description="Close/dismiss the fund transfer panel when user wants to cancel or no longer wishes to transfer funds. Use when user says 'cancel', 'never mind', 'I don't want to transfer', 'close that', 'forget it', etc.",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the authenticated user",
                },
            },
            required=["user_id"]
        )

    @classmethod
    def get_price_trend_tool(cls):
        return FunctionSchema(
            name="get_price_trend_tool",
            description="Use this tool to get the price trend of a stock over a specified period",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "The user_id of the authenticated user",
                },
                "ticker_value": {
                    "type": "array",
                    "items": {                   
                        "type": "string",
                        "enum": cls.get_dynamic_ticker_values()
                    },
                    "description": "The stock symbol to get the price trend for",
                },
                "time_history": {
                    "type": "integer",
                    "description": "The time history in years to retrieve portfolio benchmark for",
                    "default": 2,
                },
            },
            required=["user_id", "ticker_value", "time_history"]
        )