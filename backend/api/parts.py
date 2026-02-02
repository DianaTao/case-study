"""Parts API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import structlog

from database import get_db
from models import Part

logger = structlog.get_logger()
router = APIRouter()

# Import price scraper (optional - gracefully handle if not available)
try:
    from services.price_scraper import fetch_price_and_stock
    PRICE_SCRAPER_AVAILABLE = True
except ImportError:
    PRICE_SCRAPER_AVAILABLE = False
    logger.warning("Price scraper not available - refresh-price endpoint will be disabled")


@router.get("/search", response_model=List[Part])
async def search_parts(
    q: str = Query(..., description="Search query"),
    appliance_type: Optional[str] = Query(None, description="Filter by appliance type"),
    limit: int = Query(20, le=50, description="Max results")
):
    """Search for parts by query string."""
    try:
        db = get_db()
        
        # Build query
        query = db.table("parts").select("*")
        
        # Search in name, description, and part numbers
        query = query.or_(
            f"name.ilike.%{q}%,"
            f"description.ilike.%{q}%,"
            f"partselect_number.ilike.%{q}%,"
            f"manufacturer_number.ilike.%{q}%"
        )
        
        # Filter by appliance type if provided
        if appliance_type:
            query = query.eq("appliance_type", appliance_type)
        
        # Execute
        result = query.limit(limit).execute()
        
        return result.data or []
        
    except Exception as e:
        logger.error("Parts search failed", query=q, error=str(e))
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/{partselect_number}", response_model=Part)
async def get_part(partselect_number: str):
    """Get part details by PartSelect number."""
    try:
        db = get_db()
        
        result = db.table("parts").select("*").eq(
            "partselect_number", partselect_number
        ).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Part not found")
        
        return result.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get part failed", part=partselect_number, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch part")


class RefreshPriceRequest(BaseModel):
    partselect_number: str


@router.post("/refresh-price", response_model=Part)
async def refresh_price(request: RefreshPriceRequest):
    """Fetch latest price/stock for a part and update the database."""
    try:
        # Check if price scraper is available
        if not PRICE_SCRAPER_AVAILABLE:
            raise HTTPException(
                status_code=503, 
                detail="Price scraper not available. Install Playwright: pip install playwright && playwright install chromium"
            )
        
        db = get_db()
        result = db.table("parts").select("*").eq(
            "partselect_number", request.partselect_number
        ).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Part not found")

        part = result.data
        url = part.get("canonical_url") or part.get("product_url")
        if not url:
            raise HTTPException(status_code=400, detail="Part has no product URL")

        price_cents, stock_status = await fetch_price_and_stock(url)
        update_data = {}
        if price_cents is not None:
            update_data["price_cents"] = price_cents
        if stock_status:
            update_data["stock_status"] = stock_status

        if update_data:
            updated = db.table("parts").update(update_data).eq(
                "partselect_number", request.partselect_number
            ).execute()
            if updated.data:
                return updated.data[0]

        return part
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Refresh price failed", part=request.partselect_number, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to refresh price")
