import math
from typing import List

# Pricing rules as defined in the plan

def calculate_platform_fee(amount: float, item_type: str) -> float:
    """
    Calculate the platform fee.
    Products: 2% of transaction value, min $4
    Services: 3% of transaction value, min $4
    """
    if item_type.upper() == 'PRODUCT':
        fee = amount * 0.02
    elif item_type.upper() == 'SERVICE':
        fee = amount * 0.03
    else:
        fee = amount * 0.02 # default to product rules

    return max(fee, 4.0)

def calculate_protection_fee(amount: float) -> float:
    """
    Protection covers approved claims.
    1% of value, min $4.
    """
    return max(amount * 0.01, 4.0)

def calculate_escrow_fee(amount: float) -> float:
    """
    Escrow holds funds until completion is confirmed.
    1% of value, min $4.
    """
    return max(amount * 0.01, 4.0)

def calculate_delivery_fee(size: str, distance_km: float, addons: List[str] = None) -> float:
    """
    Calculate base delivery fee based on item size and distance.
    """
    if addons is None:
        addons = []
        
    size = size.upper()
    base_fee = 0.0
    
    # Distance matrix
    if distance_km <= 10:
        if size == 'SMALL':
            base_fee = 10.0
        elif size == 'MEDIUM':
            base_fee = 15.0
        elif size == 'LARGE':
            base_fee = 20.0
    elif distance_km <= 25:
        if size == 'SMALL':
            base_fee = 15.0
        elif size == 'MEDIUM':
            base_fee = 20.0
        elif size == 'LARGE':
            base_fee = 30.0
    elif distance_km <= 50:
        if size == 'SMALL':
            base_fee = 20.0
        elif size == 'MEDIUM':
            base_fee = 30.0
        elif size == 'LARGE':
            base_fee = 40.0
    else: # 50-100km and beyond (assuming 100km max for these flat rates)
        if size == 'SMALL':
            base_fee = 30.0
        elif size == 'MEDIUM':
            base_fee = 40.0
        elif size == 'LARGE':
            base_fee = 60.0
            
    # Addons pricing
    addon_fees = 0.0
    addon_pricing = {
        "EXPRESS": 10.0,
        "HEAVY_LIFT": 10.0,
        "STAIRS_ACCESS": 10.0,
        "WEEKEND": 5.0,
        "AFTER_HOURS": 10.0,
        "TWO_PERSON_LIFT": 20.0
    }
    
    for addon in addons:
        addon_fees += addon_pricing.get(addon.upper(), 0.0)
        
    return base_fee + addon_fees

def calculate_delivery_addon_fee_only(addons: List[str] = None) -> float:
    """
    Extracts only the addon fees from the delivery.
    """
    if addons is None:
        return 0.0
    
    addon_fees = 0.0
    addon_pricing = {
        "EXPRESS": 10.0,
        "HEAVY_LIFT": 10.0,
        "STAIRS_ACCESS": 10.0,
        "WEEKEND": 5.0,
        "AFTER_HOURS": 10.0,
        "TWO_PERSON_LIFT": 20.0
    }
    
    for addon in addons:
        addon_fees += addon_pricing.get(addon.upper(), 0.0)
        
    return addon_fees

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
        
    # Convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers
    return c * r
