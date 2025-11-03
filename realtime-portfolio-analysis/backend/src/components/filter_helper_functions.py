from sqlalchemy import func, and_, or_, distinct
from src.database.models import *

def get_dimension_lst():
    dimension_lst = ["Security","Instrument","Underlying", "Holding", "Ticker", "Holdings", "Asset Ticker", #Ticker
                         "Market Segment", "Vertical", "Sector", #Sector
                         "Investment Category", "Security Class", "Investment Vehicle", "Asset Type", "Asset Class", #Asset Class
                         "Asset Manager", "Investment House", "Investment Family", "Fund Group", "Fund Family", #Fund Family
                         "Concentration", "Category"
        ]
    return dimension_lst

def get_filter_levels_dict(session: Session):
    filter_levels_dict = {}

    # Query distinct asset classes
    asset_classes = session.query(distinct(AssetType.asset_class)).all()
    for (asset_class,) in asset_classes:
        filter_levels_dict[asset_class] = "asset_class"
    
    # Query distinct concentrations
    concentrations = session.query(distinct(AssetType.concentration)).all()
    for (concentration,) in concentrations:
        filter_levels_dict[concentration] = "concentration"

    # Query distinct sectors
    sectors = session.query(distinct(AssetSector.sector_name)).all()
    for (sector,) in sectors:
        filter_levels_dict[sector] = "sector"

    # Query distinct asset names
    asset_names = session.query(distinct(AssetType.asset_name)).all()
    for (asset_name,) in asset_names:
        filter_levels_dict[asset_name] = "asset_name"

    asset_tickers = session.query(distinct(AssetType.asset_ticker)).all()
    for (asset_ticker,) in asset_tickers:
        filter_levels_dict[asset_ticker] = "ticker"    

    return filter_levels_dict

def get_standardized_filter_dimesions(dimension_levels, tool_type="aggregation"):
    """
    Standardizes the filter dimensions by mapping the dimensions from a specified disctionary.
    
    Args:
        dimension_levels (list): List of dimension levels to standardize.
        
    Returns:
        list: List of standardized dimension levels.
    """
    # if tool_type != "aggregation":
        # dimension_level_mapping = {
        #     "asset_class" : "asset_class",
        #     "asset_name" : "asset_ticker",
        #     "holdings" : "asset_ticker",
        #     "ticker" : "asset_ticker",
        #     "asset_ticker" : "asset_ticker",
        #     "concentration" : "concentration",
        #     "category" : "category",
        #     "asset_manager" : "asset_manager",
        #     "sector" : "sector_name",
        #     "sector_name" : "sector_name",
        # }
    #     dimension_level_mapping ={
    #     "asset_class": ["asset_class"],
    #     "ticker": ["asset_ticker", "asset_name"],
    #     "holdings": ["asset_ticker", "asset_name"],
    #     "category": ["category"],
    #     "asset_manager": ["asset_manager"],
    #     "sector": ["sector_name", "sector"],
    #     "concentration": ["concentration"],
    #     }
    # else:
    dimension_level_mapping = {
    "ticker": ["Security", "Instrument", "Underlying", "Holdings", "Holding","Ticker", "Asset Ticker","asset_ticker"],
    "sector": ["Market Segment", "Vertical", "Sector", "Asset Sector", "Sector Name", "sector"],
    "asset_class": ["Investment Category", "Security Class", "Investment Vehicle", "Investment Type", "Asset Type", "Asset Class", "asset_class"],
    "asset_manager": ["Asset Manager", "Fund Manager", "Investment House", "Investment Family", "Fund Group", "Fund Family", "asset_manager"],
    "concentration": ["Concentration"],
    "category": ["Category"]
    }

    reverse_mapping = {value.lower(): key for key, values in dimension_level_mapping.items() for value in values}

    # Replace dimension levels with corresponding keys (case-insensitive)
    standardized_levels = [reverse_mapping.get(level.lower(), level) for level in dimension_levels]   
       
    # standardized_levels = []
    # for level in dimension_levels:
    #     if level in dimension_level_mapping:
    #         standardized_level = dimension_level_mapping.get(level, level)
    #         standardized_levels.append(standardized_level)
        
    return standardized_levels

def get_filters_dict(filter_levels_dict, filter_values):
    filter_levels = [filter_levels_dict.get(value) for value in filter_values] if filter_values else []
    filter_levels = list(set(filter_levels))  # Remove duplicates

    filters = {} 

    for v in filter_values:
        if v=="Mutual Funds":
            v = "Mutual Fund"
        if filter_levels_dict.get(v) not in filters:
            filters[filter_levels_dict.get(v)] = [v]
        else:
            filters[filter_levels_dict.get(v)].append(v)
    
    return filters