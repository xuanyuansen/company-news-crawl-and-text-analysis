from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.services.database_service import db_service

router = APIRouter()

@router.get("")
async def get_news(
    db: Optional[str] = Query(None, description="Database name"),
    collection: Optional[str] = Query(None, description="Collection name"),
    limit: int = Query(100, ge=1, le=1000),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
) -> Dict[str, Any]:
    """Get news list with optional filtering"""
    
    if db and collection:
        result = db_service.get_documents(db, collection, limit)
        return {
            "news": result["documents"],
            "total": result["total"]
        }
    
    # If no specific db/collection, search across all news dbs
    all_news = []
    news_dbs = ["east_money_news", "jrj_news", "nbd_news", "net_ease_news"]
    
    for db_name in news_dbs:
        try:
            cols = db_service.get_collections(db_name)
            for col in cols[:2]:  # Limit to first 2 collections per db
                result = db_service.get_documents(db_name, col["name"], min(limit, 20))
                for doc in result["documents"]:
                    doc["_db"] = db_name
                    doc["_collection"] = col["name"]
                all_news.extend(result["documents"])
                if len(all_news) >= limit:
                    break
            if len(all_news) >= limit:
                break
        except Exception:
            continue
    
    return {
        "news": all_news[:limit],
        "total": len(all_news)
    }

@router.get("/sentiment/distribution")
async def get_sentiment_distribution() -> Dict[str, Any]:
    """Get sentiment distribution across all news"""
    return {"distribution": db_service.get_sentiment_distribution()}

@router.get("/sentiment/trend")
async def get_sentiment_trend(days: int = Query(30, ge=1, le=365)) -> Dict[str, Any]:
    """Get sentiment trend over time"""
    # Generate mock trend data for now
    # In real implementation, this would aggregate from database
    trend = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i-1)).strftime("%Y-%m-%d")
        trend.append({
            "date": date,
            "good": max(0, 50 + i * 2 - (i % 7) * 10),
            "bad": max(0, 30 - i + (i % 5) * 5),
            "neutral": max(0, 20 + (i % 3) * 5)
        })
    
    return {"trend": trend}

@router.get("/hot-stocks")
async def get_hot_stocks() -> Dict[str, Any]:
    """Get hot stocks by news count"""
    return {"stocks": db_service.get_hot_stocks(limit=20)}
