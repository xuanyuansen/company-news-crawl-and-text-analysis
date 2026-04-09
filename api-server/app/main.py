from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import dashboard, crawler, news, database

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(crawler.router, prefix=f"{settings.API_V1_STR}/crawler", tags=["crawler"])
app.include_router(news.router, prefix=f"{settings.API_V1_STR}/news", tags=["news"])
app.include_router(database.router, prefix=f"{settings.API_V1_STR}/database", tags=["database"])

@app.get("/")
async def root():
    return {"message": "FinNews Hunter API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
