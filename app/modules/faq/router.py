from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from app.modules.faq import service, schemas
from app.modules.admin.router import get_current_admin

router = APIRouter(prefix="/faq", tags=["FAQ"])

@router.get("/", response_model=List[schemas.FAQResponse])
async def list_faqs(category: Optional[str] = None):
    return await service.get_all_faqs(category)

@router.get("/{faq_id}", response_model=schemas.FAQResponse)
async def get_faq(faq_id: int):
    return await service.get_faq_by_id(faq_id)

@router.post("/", response_model=schemas.FAQResponse)
async def create_faq(data: schemas.FAQCreate, admin=Depends(get_current_admin)):
    return await service.create_faq(data)

@router.patch("/{faq_id}", response_model=schemas.FAQResponse)
async def update_faq(faq_id: int, data: schemas.FAQUpdate, admin=Depends(get_current_admin)):
    return await service.update_faq(faq_id, data)

@router.delete("/{faq_id}")
async def delete_faq(faq_id: int, admin=Depends(get_current_admin)):
    return await service.delete_faq(faq_id)
