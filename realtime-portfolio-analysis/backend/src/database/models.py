from sqlalchemy import Column, Integer, String, Float, Date, Text, JSON, ForeignKey, func, select, TIMESTAMP
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.hybrid import hybrid_property
from src.database.database import Base
from datetime import date

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    username = Column(String(150), nullable=False, unique=True)
    email = Column(String(150), nullable=False, unique=True, index=True)
    password = Column(String(200), nullable=False)
    dob = Column(Date, nullable=False)
    phone_number = Column(String(11), nullable=False, unique=True, index=True)

    portfolio = relationship("UserPortfolio", backref="user", cascade="all, delete-orphan")
    transactions = relationship("UserTransactions", backref="user", cascade="all, delete-orphan")
    orders = relationship("OrderBook", backref="user", cascade="all, delete-orphan")
    bank_accounts = relationship("UserBankAccount", backref="user", cascade="all, delete-orphan")

class AssetType(Base):
    __tablename__ = 'asset_type'

    asset_id = Column(Integer, primary_key=True)
    asset_ticker = Column(String(10), nullable=False, unique=True)
    asset_name = Column(String(200), nullable=False)
    asset_class = Column(String(100), nullable=False)
    net_expense_ratio = Column(Float, nullable=True)
    morningstar_rating = Column(Float, nullable=True)
    maturity_date = Column(Date, nullable=True)
    one_yr_volatility = Column(Float, nullable=True)
    similar_asset = Column(Text, nullable=True)
    category = Column(String(200), nullable=True)
    asset_manager = Column(String(200), nullable=True)
    portfolio_composition = Column(JSON, nullable=True)
    bond_rating = Column(Float, nullable=True)
    concentration = Column(String(200), nullable=True)  # Added concentration and removed legal_type

    sectors = relationship("AssetSector", backref="asset", cascade="all, delete-orphan")
    history = relationship("AssetHistory", backref="asset", cascade="all, delete-orphan")
    portfolio = relationship("UserPortfolio", backref="asset", cascade="all, delete-orphan")
    transactions = relationship("UserTransactions", backref="asset", cascade="all, delete-orphan")
    benchmark = relationship("DefaultBenchmarks", backref="asset", cascade="all, delete-orphan")

class AssetSector(Base):
    __tablename__ = 'asset_sector'

    asset_sec_id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey('asset_type.asset_id', ondelete='CASCADE'), nullable=False)
    sector_symbol = Column(String(200), nullable=False)
    sector_name = Column(String(200), nullable=False)
    sector_weightage = Column(Float, nullable=False)

class AssetHistory(Base):
    __tablename__ = 'asset_history'

    asset_hist_id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey('asset_type.asset_id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    close_price = Column(Float, nullable=False)

    @classmethod
    def get_extended_data(cls, session: Session, user_id: int):
        user_portfolio = session.query(
            UserPortfolio.asset_id,
            UserPortfolio.asset_total_units
        ).filter(UserPortfolio.user_id == user_id).subquery()

        query = (
            session.query(
                cls.asset_hist_id,
                cls.asset_id,
                cls.date,
                cls.close_price,
                AssetType.asset_class,
                AssetType.asset_name,
                AssetType.concentration,
                AssetType.asset_manager,
                AssetType.category,
                AssetType.asset_ticker.label('ticker'),
                AssetSector.sector_name.label('sector'),
                AssetSector.sector_weightage,
                user_portfolio.c.asset_total_units
            )
            .join(AssetType, cls.asset_id == AssetType.asset_id)
            .outerjoin(AssetSector, AssetType.asset_id == AssetSector.asset_id)
            .join(user_portfolio, cls.asset_id == user_portfolio.c.asset_id)
        )

        return query.all()

class UserPortfolio(Base):
    __tablename__ = 'user_portfolio'

    user_port_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    asset_id = Column(Integer, ForeignKey('asset_type.asset_id', ondelete='CASCADE'), nullable=False)
    asset_total_units = Column(Float, nullable=False, default=0)
    avg_cost_per_unit = Column(Float, nullable=False, default=0)
    investment_amount = Column(Float, nullable=False, default=0)

    @hybrid_property
    def latest_close_price(self):
        session = Session.object_session(self)
        latest_price = session.query(AssetHistory.close_price).filter(AssetHistory.asset_id == self.asset_id).order_by(AssetHistory.date.desc()).first()
        return latest_price[0] if latest_price else None

    @latest_close_price.expression
    def latest_close_price(cls):
        return select(AssetHistory.close_price)\
            .where(AssetHistory.asset_id == cls.asset_id)\
            .order_by(AssetHistory.date.desc())\
            .limit(1)\
            .scalar_subquery()

    @hybrid_property
    def current_amount(self):
        return self.asset_total_units * self.latest_close_price if self.latest_close_price else 0.0

    @current_amount.expression
    def current_amount(cls):
        return cls.asset_total_units * func.coalesce(cls.latest_close_price, 0)
    
    @hybrid_property
    def sector_weighted_current_amount(self):
        session = Session.object_session(self)
        weightage = session.query(AssetSector.sector_weightage)\
            .filter(AssetSector.asset_id == self.asset_id)\
            .scalar()
        
        if weightage is None:
            weightage = 1.0  # Default to 1.0 if no sector weightage is found
        
        return self.asset_total_units * self.latest_close_price * weightage

    @sector_weighted_current_amount.expression
    def sector_weighted_current_amount(cls):
        return cls.asset_total_units * func.coalesce(cls.latest_close_price, 0) * \
               func.coalesce(
                   select(AssetSector.sector_weightage)
                   .where(AssetSector.asset_id == cls.asset_id)
                   .correlate(cls)
                   .scalar_subquery(),
                   1.0
               )

    @classmethod
    def get_total_current_amount(cls, session: Session, user_id: int):
        user_portfolios = session.query(cls).filter(cls.user_id == user_id).all()
        return sum(portfolio.current_amount for portfolio in user_portfolios)
    

class UserTransactions(Base):
    __tablename__ = 'user_transactions'

    trans_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    asset_id = Column(Integer, ForeignKey('asset_type.asset_id', ondelete='CASCADE'), nullable=False)
    trans_type = Column(String(5), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    units = Column(Float, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)

class DefaultBenchmarks(Base):
    __tablename__ = 'default_benchmarks'

    benchmark_id = Column(Integer, primary_key=True)
    benchamark_asset_id = Column(Integer, ForeignKey('asset_type.asset_id', ondelete='CASCADE'), nullable=False)
    benchmark_for_asset_class = Column(String(100), nullable=False)

class AssetClassRiskLevelMapping(Base):
    __tablename__ = 'asset_class_risk_level_mapping'

    asset_risk_id = Column(Integer, primary_key=True)
    asset_type = Column(String(100), nullable=False)  # Renamed from invst_type
    volatility_range_start = Column(Float, nullable=False)
    volatility_range_end = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)  # Renamed from risk_level
    concentration = Column(String(200), nullable=True)  # Added concentration
    score1 = Column(Float, nullable=True)  # Added score1
    addon1 = Column(Float, nullable=True)  # Added addon1
    addon2 = Column(Float, nullable=True)  # Added addon2

class RelativeBenchmark(Base):
    __tablename__ = 'relative_benchmarks'

    id = Column(Integer, primary_key=True)
    asset_ticker = Column(String(10), nullable=False, unique=True)
    asset_name = Column(String(200), nullable=False)
    relative_benchmark = Column(String(10), nullable=False)

class OrderBook(Base):
    __tablename__ = 'order_book'

    order_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    asset_id = Column(Integer, ForeignKey('asset_type.asset_id', ondelete='CASCADE'), nullable=False)
    order_type = Column(String(15), nullable=False)  # e.g., Limit or Market Open
    symbol = Column(String(10), nullable=False)
    description = Column(String(200), nullable=True)
    buy_sell = Column(String(4), nullable=False)  # e.g., Buy or Sell
    unit_price = Column(Float, nullable=False)
    limit_price = Column(Float, nullable=True)  # Only for Limit orders
    qty = Column(Float, nullable=False)  # Quantity of units
    amount = Column(Float, nullable=False)  # Total amount for the order
    settlement_date = Column(Date, nullable=False, default=date.today)
    order_status = Column(String(20), nullable=False, default='Pending')  # e.g., Pending, Completed, Cancelled
    order_date = Column(TIMESTAMP, nullable=False, default=func.now())

    asset = relationship("AssetType", backref="order_book")

class UserBankAccount(Base):
    __tablename__ = 'user_bank_accounts'

    bank_account_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    bank_name = Column(String(100), nullable=False)
    account_number = Column(String(20), nullable=False)  # Masked format: ***1234
    account_type = Column(String(50), nullable=False)  # Checking, Savings, Money Market
    available_balance = Column(Float, nullable=False, default=0.0)
    is_active = Column(Integer, nullable=False, default=1)  # 1 for active, 0 for inactive