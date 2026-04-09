from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.services.database_service import db_service

router = APIRouter()

class QueryRequest(BaseModel):
    db: str
    collection: str
    query: Dict[str, Any]
    limit: int = 100

@router.get("/stats")
async def get_database_stats() -> Dict[str, Any]:
    """Get statistics for all databases"""
    return {"databases": db_service.get_database_stats()}

@router.get("/{db}/collections")
async def get_collections(db: str) -> Dict[str, Any]:
    """Get collections for a database"""
    return {"collections": db_service.get_collections(db)}

@router.get("/{db}/{collection}/docs")
async def get_documents(
    db: str,
    collection: str,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Get documents from a collection"""
    return db_service.get_documents(db, collection, limit, skip)

@router.post("/query")
async def query_documents(request: QueryRequest) -> Dict[str, Any]:
    """Execute a custom query"""
    documents = db_service.query_documents(
        request.db,
        request.collection,
        request.query,
        request.limit
    )
    return {"documents": documents}
