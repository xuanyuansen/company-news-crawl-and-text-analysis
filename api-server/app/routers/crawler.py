from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List

from app.services.crawler_service import crawler_service

router = APIRouter()

class CrawlerStartRequest(BaseModel):
    site: str
    mode: str = "one_day"

class CrawlerStopRequest(BaseModel):
    site: str

@router.get("/sites")
async def get_crawler_sites() -> Dict[str, List[Dict[str, Any]]]:
    """Get all crawler site configurations"""
    return {"sites": crawler_service.get_sites()}

@router.post("/start")
async def start_crawler(request: CrawlerStartRequest) -> Dict[str, Any]:
    """Start a crawler"""
    return crawler_service.start_crawler(request.site, request.mode)

@router.post("/stop")
async def stop_crawler(request: CrawlerStopRequest) -> Dict[str, Any]:
    """Stop a crawler"""
    return crawler_service.stop_crawler(request.site)

@router.get("/status")
async def get_crawler_status() -> Dict[str, Any]:
    """Get current crawler status"""
    return crawler_service.get_status()

@router.post("/report")
async def generate_report(days: int = 3) -> Dict[str, Any]:
    """Generate news report"""
    return crawler_service.generate_report(days)
