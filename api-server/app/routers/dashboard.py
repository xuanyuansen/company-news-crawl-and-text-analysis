from fastapi import APIRouter
from typing import Dict, Any

from app.services.database_service import db_service
from app.services.crawler_service import crawler_service

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats() -> Dict[str, Any]:
    """Get dashboard statistics"""
    return {
        "mongodb_connected": db_service.is_connected(),
        "today_news_count": db_service.get_today_news_count(),
        "sentiment_distribution": db_service.get_sentiment_distribution(),
        "hot_stocks": db_service.get_hot_stocks(limit=10)
    }

@router.get("/tasks")
async def get_recent_tasks() -> Dict[str, Any]:
    """Get recent crawler tasks"""
    return {
        "tasks": crawler_service.get_recent_tasks(limit=5)
    }
