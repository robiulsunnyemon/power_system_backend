from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from typing import List, Optional
from app.modules.reports import service, schemas
from app.modules.users.router import get_current_user_id
from app.core.db import db
from prisma.enums import Role, ReportStatus

router = APIRouter(prefix="/reports", tags=["User Reports"])

async def check_admin_role(user_id: int = Depends(get_current_user_id)):
    user = await db.user.find_unique(where={"id": user_id})
    if not user or Role.ADMIN not in user.roles:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Admin only"
        )
    return user_id

@router.post("/user/{user_id}", response_model=schemas.ReportResponse, status_code=status.HTTP_201_CREATED)
async def report_user_endpoint(
    data: schemas.ReportCreate,
    user_id: int = Path(..., title="ID of the user to report"),
    reporter_id: int = Depends(get_current_user_id)
):
    """
    Endpoint for any authenticated user to report another user.
    """
    return await service.create_report(reporter_id, user_id, data)

@router.get("/", response_model=schemas.PaginatedReportResponse)
async def get_reports_endpoint(
    status: Optional[ReportStatus] = Query(None, description="Filter by report status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    admin_id: int = Depends(check_admin_role)
):
    """
    Admin endpoint to view all reports with pagination.
    """
    return await service.get_reports(status, page, page_size)

@router.patch("/{report_id}/resolve", response_model=schemas.ReportResponse)
async def resolve_report_endpoint(
    data: schemas.ReportResolveRequest,
    report_id: int = Path(..., title="ID of the report to resolve"),
    admin_id: int = Depends(check_admin_role)
):
    """
    Admin endpoint to resolve a report and take action.
    Admin can perform this type of action: ACTIVE,PENDING,DEACTIVE,SUSPEND,DELETE,DISMISS_REPORT
    """
    return await service.resolve_report(report_id, data)
