from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from prisma.enums import BugCategory, BugSeverity, BugStatus

class BugReportCreate(BaseModel):
    subject: str
    category: BugCategory
    severity: BugSeverity
    description: str
    deviceModel: Optional[str] = None
    browserVersion: Optional[str] = None
    sessionId: Optional[str] = None

class BugReportResolve(BaseModel):
    status: BugStatus

class ReporterInfo(BaseModel):
    id: int
    fullname: str
    email: str
    profile_image: Optional[str] = None

class BugReportResponse(BaseModel):
    id: int
    subject: str
    category: BugCategory
    severity: BugSeverity
    description: str
    attachmentUrl: Optional[str] = None
    deviceModel: Optional[str] = None
    browserVersion: Optional[str] = None
    sessionId: Optional[str] = None
    status: BugStatus
    userId: int
    reporter: Optional[ReporterInfo] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

class PaginatedBugReportResponse(BaseModel):
    total: int
    page: int
    page_size: int
    bugs: List[BugReportResponse]
