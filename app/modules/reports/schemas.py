from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from prisma.enums import ReportReason, ReportStatus
from enum import Enum

class ReportUserInfo(BaseModel):
    id: int
    fullname: str
    displayname: Optional[str] = None
    profile_image: Optional[str] = None

class ReportCreate(BaseModel):
    reason: ReportReason
    description: Optional[str] = None

class ReportAction(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    DEACTIVE = "DEACTIVE"
    SUSPEND = "SUSPEND"
    DELETE = "DELETE"
    DISMISS_REPORT = "DISMISS_REPORT"

class ReportResolveRequest(BaseModel):
    adminAction: ReportAction

class ReportResponse(BaseModel):
    id: int
    reason: ReportReason
    description: Optional[str]
    status: ReportStatus
    adminAction: Optional[str]
    reporterId: int
    reportedUserId: int
    reporter: Optional[ReportUserInfo] = None
    reportedUser: Optional[ReportUserInfo] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

class PaginatedReportResponse(BaseModel):
    total: int
    page: int
    page_size: int
    reports: List[ReportResponse]
