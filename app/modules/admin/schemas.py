from pydantic import BaseModel
from enum import Enum
from typing import List
from prisma.enums import AccountStatus

class UserRoleFilter(str, Enum):
    ALL = "ALL"
    USER = "USER"
    SELLER = "SELLER"
    SERVICE_PROVIDER = "SERVICE_PROVIDER"
    ADMIN = "ADMIN"

class UpdateStatusRequest(BaseModel):
    accountStatus: AccountStatus

class DashboardStatsResponse(BaseModel):
    total_users: int
    active_users: int
    pending_users: int
    total_growth_pct: float
    active_growth_pct: float
    pending_growth_pct: float

class GrowthDataPoint(BaseModel):
    label: str # e.g. "Mon", "May", "2024"
    count: int

class GrowthResponse(BaseModel):
    data: List[GrowthDataPoint]

class GrowthFilter(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SIX_MONTHS = "6months"
    YEARLY = "yearly"
    YEAR_RANGE = "year_range"
