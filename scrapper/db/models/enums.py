from enum import Enum, auto

class RetailerType(str, Enum):
    """Enum for retailer types"""
    DIRECT_RETAILER = "DIRECT_RETAILER"
    PRICE_COMPARER = "PRICE_COMPARER"

class Currency(str, Enum):
    """Enum for currencies"""
    HUF = "HUF"
    CZK = "CZK" 