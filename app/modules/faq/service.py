from app.core.db import db
from app.modules.faq.schemas import FAQCreate, FAQUpdate
from fastapi import HTTPException

async def create_faq(data: FAQCreate):
    return await db.faq.create(
        data={
            "question": data.question,
            "answer": data.answer,
            "category": data.category
        }
    )

async def get_all_faqs(category: str = None):
    where = {}
    if category:
        where["category"] = category
    return await db.faq.find_many(where=where, order={"createdAt": "desc"})

async def get_faq_by_id(faq_id: int):
    faq = await db.faq.find_unique(where={"id": faq_id})
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return faq

async def update_faq(faq_id: int, data: FAQUpdate):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    faq = await db.faq.find_unique(where={"id": faq_id})
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    
    return await db.faq.update(
        where={"id": faq_id},
        data=update_data
    )

async def delete_faq(faq_id: int):
    faq = await db.faq.find_unique(where={"id": faq_id})
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    
    await db.faq.delete(where={"id": faq_id})
    return {"message": "FAQ deleted successfully"}
