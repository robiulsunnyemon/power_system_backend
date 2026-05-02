from pydantic import BaseModel
from enum import Enum
from prisma.enums import AccountStatus

class UserRoleFilter(str, Enum):
    ALL = "ALL"
    USER = "USER"
    SELLER = "SELLER"
    SERVICE_PROVIDER = "SERVICE_PROVIDER"
    ADMIN = "ADMIN"

class UpdateStatusRequest(BaseModel):
    accountStatus: AccountStatus
