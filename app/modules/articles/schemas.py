from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ArticleBase(BaseModel):
    title: str
    description: str
    category: str

class ArticleCreate(ArticleBase):
    pass

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None

class ArticleResponse(ArticleBase):
    id: int
    image_url: Optional[str]
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True
