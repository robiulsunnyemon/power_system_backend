from app.core.db import db
from fastapi import UploadFile, HTTPException
from app.common.cloudinary import upload_image
from app.modules.bugs.schemas import BugReportCreate, BugReportResolve
from prisma.enums import BugStatus

def format_bug_response(bug):
    """
    Helper to format bug report response, flattening reporter profile image.
    """
    b_dict = bug.model_dump()
    if bug.reporter:
        b_dict["reporter"] = {
            "id": bug.reporter.id,
            "fullname": bug.reporter.fullname,
            "email": bug.reporter.email,
            "profile_image": bug.reporter.profile.profile_image if bug.reporter.profile else None
        }
    return b_dict

async def create_bug_report(user_id: int, data: BugReportCreate, file: UploadFile = None):
    attachment_url = None
    if file:
        upload_result = await upload_image(file)
        if upload_result:
            attachment_url = upload_result.get("secure_url")

    bug = await db.bugreport.create(
        data={
            "subject": data.subject,
            "category": data.category,
            "severity": data.severity,
            "description": data.description,
            "attachmentUrl": attachment_url,
            "deviceModel": data.deviceModel,
            "browserVersion": data.browserVersion,
            "sessionId": data.sessionId,
            "userId": user_id
        },
        include={"reporter": {"include": {"profile": True}}}
    )
    return format_bug_response(bug)

async def get_bug_reports(status: BugStatus = None):
    where = {}
    if status:
        where["status"] = status
        
    bugs = await db.bugreport.find_many(
        where=where,
        include={"reporter": {"include": {"profile": True}}},
        order={"createdAt": "desc"}
    )
    return [format_bug_response(b) for b in bugs]

async def resolve_bug_report(bug_id: int, data: BugReportResolve):
    bug = await db.bugreport.find_unique(where={"id": bug_id})
    if not bug:
        raise HTTPException(status_code=404, detail="Bug report not found")
        
    updated_bug = await db.bugreport.update(
        where={"id": bug_id},
        data={"status": data.status},
        include={"reporter": {"include": {"profile": True}}}
    )
    return format_bug_response(updated_bug)
