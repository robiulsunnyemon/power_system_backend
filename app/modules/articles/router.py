from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from app.modules.articles import service, schemas
from app.modules.admin.router import get_current_admin
import json

router = APIRouter(prefix="/articles", tags=["Article Section"])

@router.get("/", response_model=List[schemas.ArticleResponse])
async def list_articles(category: Optional[str] = None):
    return await service.get_all_articles(category)

@router.get("/{article_id}", response_model=schemas.ArticleResponse)
async def get_article(article_id: int):
    return await service.get_article_by_id(article_id)

@router.post("/", response_model=schemas.ArticleResponse)
async def create_article(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    image: Optional[UploadFile] = File(None),
    admin=Depends(get_current_admin)
):
    data = schemas.ArticleCreate(title=title, description=description, category=category)
    return await service.create_article(data, image)

@router.patch("/{article_id}", response_model=schemas.ArticleResponse)
async def update_article(
    article_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    admin=Depends(get_current_admin)
):
    data = schemas.ArticleUpdate(title=title, description=description, category=category)
    return await service.update_article(article_id, data, image)

@router.delete("/{article_id}")
async def delete_article(article_id: int, admin=Depends(get_current_admin)):
    return await service.delete_article(article_id)
