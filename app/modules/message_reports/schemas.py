from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
from app.modules.reports.schemas import ReportReason, ReportStatus, ReportAction
from app.modules.users.schemas import UserProfileResponse

class MessageReportCreate(BaseModel):
    reason: ReportReason
    description: Optional[str] = None

class MessageReportResponse(BaseModel):
    id: int
    reason: ReportReason
    description: Optional[str]
    image_url: Optional[str]
    status: ReportStatus
    adminAction: Optional[str]
    reporterId: int
    reportedUserId: int
    reporter: Optional[UserProfileResponse]
    reportedUser: Optional[UserProfileResponse]
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

class PaginatedMessageReportResponse(BaseModel):
    total: int
    page: int
    page_size: int
    reports: List[MessageReportResponse]

class MessageReportResolveRequest(BaseModel):
    adminAction: ReportAction
