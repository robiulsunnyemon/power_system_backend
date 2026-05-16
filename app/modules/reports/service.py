from app.core.db import db
from fastapi import HTTPException
from app.modules.reports.schemas import ReportCreate, ReportResolveRequest, ReportAction
from prisma.enums import ReportStatus, AccountStatus

async def create_report(reporter_id: int, reported_user_id: int, data: ReportCreate):
    if reporter_id == reported_user_id:
        raise HTTPException(status_code=400, detail="You cannot report yourself")
        
    reported_user = await db.user.find_unique(where={"id": reported_user_id})
    if not reported_user:
        raise HTTPException(status_code=404, detail="Reported user not found")
        
    report = await db.userreport.create(
        data={
            "reason": data.reason,
            "description": data.description,
            "reporter": {"connect": {"id": reporter_id}},
            "reportedUser": {"connect": {"id": reported_user_id}}
        },
        include={
            "reporter": {"include": {"profile": True}},
            "reportedUser": {"include": {"profile": True}}
        }
    )
    
    return report

async def get_reports(status: str = None, page: int = 1, page_size: int = 10):
    where = {}
    if status:
        where["status"] = status
        
    total = await db.userreport.count(where=where)
    
    reports = await db.userreport.find_many(
        where=where,
        include={
            "reporter": {"include": {"profile": True}},
            "reportedUser": {"include": {"profile": True}}
        },
        order={"createdAt": "desc"},
        skip=(page - 1) * page_size,
        take=page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "reports": reports
    }

async def resolve_report(report_id: int, data: ReportResolveRequest):
    report = await db.userreport.find_unique(
        where={"id": report_id},
        include={"reportedUser": True}
    )
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        

    admin_action = data.adminAction
    
    if admin_action != ReportAction.DISMISS_REPORT:
        # admin_action is an AccountStatus (ACTIVE, PENDING, DEACTIVE, SUSPEND, DELETE)
        new_account_status = AccountStatus[admin_action.value]
        
        # Determine if we should increment tokenVersion (to force logout)
        update_data = {"accountStatus": new_account_status}
        if new_account_status in [AccountStatus.SUSPEND, AccountStatus.DELETE, AccountStatus.DEACTIVE]:
            update_data["tokenVersion"] = {"increment": 1}
            
        # Update user status
        await db.user.update(
            where={"id": report.reportedUserId},
            data=update_data
        )
        
        display_action = admin_action.value
    else:
        display_action = "DISMISSED"

    # Update report status
    updated_report = await db.userreport.update(
        where={"id": report_id},
        data={
            "status": ReportStatus.RESOLVED,
            "adminAction": display_action
        },
        include={
            "reporter": {"include": {"profile": True}},
            "reportedUser": {"include": {"profile": True}}
        }
    )
    
    return updated_report
