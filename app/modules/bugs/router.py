from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from typing import List, Optional
from app.modules.bugs import service, schemas
from app.modules.users.router import get_current_user_id
from app.modules.admin.router import get_current_admin
from prisma.enums import BugStatus, BugCategory, BugSeverity

router = APIRouter(prefix="/bugs", tags=["Bug Reports"])

@router.post("/", response_model=schemas.BugReportResponse, status_code=status.HTTP_201_CREATED)
async def create_bug(
    subject: str = Form(...),
    category: BugCategory = Form(...),
    severity: BugSeverity = Form(...),
    description: str = Form(...),
    deviceModel: Optional[str] = Form(None),
    browserVersion: Optional[str] = Form(None),
    sessionId: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    user_id: int = Depends(get_current_user_id)
):
    """
    Endpoint for any authenticated user to report a bug.
    """
    data = schemas.BugReportCreate(
        subject=subject,
        category=category,
        severity=severity,
        description=description,
        deviceModel=deviceModel,
        browserVersion=browserVersion,
        sessionId=sessionId
    )
    return await service.create_bug_report(user_id, data, file)

@router.get("/", response_model=schemas.PaginatedBugReportResponse)
async def list_bugs(
    status: Optional[BugStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    admin=Depends(get_current_admin)
):
    """
    Admin only: List all bug reports with pagination.
    """
    return await service.get_bug_reports(status, page, page_size)

@router.patch("/{bug_id}/resolve", response_model=schemas.BugReportResponse)
async def resolve_bug(
    bug_id: int,
    data: schemas.BugReportResolve,
    admin=Depends(get_current_admin)
):
    """
    Admin only: Update the status of a bug report.
    """
    return await service.resolve_bug_report(bug_id, data)
