from app.core.db import db
from app.modules.articles.schemas import ArticleCreate, ArticleUpdate
from fastapi import HTTPException, UploadFile
from app.common.cloudinary import upload_image, delete_image, get_public_id_from_url

async def create_article(data: ArticleCreate, image: UploadFile = None):
    image_url = None
    if image:
        upload_res = await upload_image(image, folder="jorden/articles")
        if upload_res:
            image_url = upload_res.get("secure_url")
            
    return await db.articlesection.create(
        data={
            "title": data.title,
            "description": data.description,
            "category": data.category,
            "image_url": image_url
        }
    )

async def get_all_articles(category: str = None):
    where = {}
    if category:
        where["category"] = category
    return await db.articlesection.find_many(where=where, order={"createdAt": "desc"})

async def get_article_by_id(article_id: int):
    article = await db.articlesection.find_unique(where={"id": article_id})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

async def update_article(article_id: int, data: ArticleUpdate, image: UploadFile = None):
    article = await db.articlesection.find_unique(where={"id": article_id})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if image:
        # Delete old image if exists
        if article.image_url:
            public_id = get_public_id_from_url(article.image_url)
            if public_id:
                await delete_image(public_id)
        
        # Upload new image
        upload_res = await upload_image(image, folder="jorden/articles")
        if upload_res:
            update_data["image_url"] = upload_res.get("secure_url")
            
    return await db.articlesection.update(
        where={"id": article_id},
        data=update_data
    )

async def delete_article(article_id: int):
    article = await db.articlesection.find_unique(where={"id": article_id})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Delete image from Cloudinary
    if article.image_url:
        public_id = get_public_id_from_url(article.image_url)
        if public_id:
            await delete_image(public_id)
            
    await db.articlesection.delete(where={"id": article_id})
    return {"message": "Article deleted successfully"}
