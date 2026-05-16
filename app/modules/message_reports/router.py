from fastapi import APIRouter, Depends, HTTPException, status, Path, Query, UploadFile, File, Form
from typing import Optional
from app.modules.message_reports import service, schemas
from app.modules.users.router import get_current_user_id
from app.modules.reports.schemas import ReportReason, ReportStatus
from app.core.db import db
from prisma.enums import Role

router = APIRouter(prefix="/message-reports", tags=["Message Reports"])

async def check_admin_role(user_id: int = Depends(get_current_user_id)):
    user = await db.user.find_unique(where={"id": user_id})
    if not user or Role.ADMIN not in user.roles:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Admin only"
        )
    return user_id

@router.post("/user/{user_id}", response_model=schemas.MessageReportResponse, status_code=status.HTTP_201_CREATED)
async def report_message_user_endpoint(
    user_id: int = Path(..., title="ID of the user to report"),
    reason: ReportReason = Form(...),
    description: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    reporter_id: int = Depends(get_current_user_id)
):
    """
    Endpoint for any authenticated user to report another user for message violations.
    """
    data = schemas.MessageReportCreate(reason=reason, description=description)
    return await service.create_message_report(reporter_id, user_id, data, file)

@router.get("/", response_model=schemas.PaginatedMessageReportResponse)
async def get_message_reports_endpoint(
    status: Optional[ReportStatus] = Query(None, description="Filter by report status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    admin_id: int = Depends(check_admin_role)
):
    """
    Admin endpoint to view all message reports with pagination.
    """
    return await service.get_message_reports(status, page, page_size)

@router.patch("/{report_id}/resolve", response_model=schemas.MessageReportResponse)
async def resolve_message_report_endpoint(
    data: schemas.MessageReportResolveRequest,
    report_id: int = Path(..., title="ID of the report to resolve"),
    admin_id: int = Depends(check_admin_role)
):
    """
    Admin endpoint to resolve a message report and take action.
    """
    return await service.resolve_message_report(report_id, data)
