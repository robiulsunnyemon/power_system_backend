from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.db import connect_db, disconnect_db
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.admin.router import router as admin_router
from app.modules.products.router import router as products_router
from app.modules.orders.router import router as orders_router
from app.modules.reviews.router import router as reviews_router
from app.modules.messages.router import router as messages_router
from app.modules.services.router import router as services_router
from app.modules.service_applications.router import router as service_applications_router
from app.modules.reports.router import router as reports_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await disconnect_db()

app = FastAPI(
    title="Jorden Backend API",
    description="FastAPI, Prisma, PostgreSQL Backend",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(reviews_router)
app.include_router(messages_router)
app.include_router(services_router)
app.include_router(service_applications_router)
app.include_router(reports_router)

@app.get("/")
async def root():
    return {"message": "Welcome to Jorden API"}
