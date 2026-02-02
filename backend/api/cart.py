"""Cart API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import structlog

from database import get_db

logger = structlog.get_logger()
router = APIRouter()


class AddToCartRequest(BaseModel):
    cart_id: str
    partselect_number: str
    quantity: int = 1


@router.post("/add")
async def add_to_cart(request: AddToCartRequest):
    """Add item to cart."""
    try:
        db = get_db()
        
        # Ensure cart exists
        cart_result = db.table("carts").select("id").eq("id", request.cart_id).execute()
        if not cart_result.data:
            db.table("carts").insert({"id": request.cart_id, "status": "active"}).execute()
        
        # Check if item already in cart
        existing = db.table("cart_items").select("*").eq(
            "cart_id", request.cart_id
        ).eq("partselect_number", request.partselect_number).execute()
        
        if existing.data:
            # Update quantity
            new_qty = existing.data[0]["quantity"] + request.quantity
            db.table("cart_items").update({"quantity": new_qty}).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            # Insert new item
            db.table("cart_items").insert({
                "cart_id": request.cart_id,
                "partselect_number": request.partselect_number,
                "quantity": request.quantity
            }).execute()
        
        # Return updated cart
        return await get_cart(request.cart_id)
        
    except Exception as e:
        logger.error("Add to cart failed", cart_id=request.cart_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to add to cart")


@router.get("/{cart_id}")
async def get_cart(cart_id: str):
    """Get cart contents."""
    try:
        db = get_db()
        
        # Get cart items
        cart_items_result = db.table("cart_items").select("*").eq("cart_id", cart_id).execute()
        items_raw = cart_items_result.data or []
        
        # Manually fetch part details for each item
        items = []
        for item in items_raw:
            part_result = db.table("parts").select("*").eq(
                "partselect_number", item["partselect_number"]
            ).execute()
            
            if part_result.data:
                part = part_result.data[0]
                items.append({
                    "id": item["id"],
                    "cart_id": item["cart_id"],
                    "partselect_number": item["partselect_number"],
                    "quantity": item["quantity"],
                    "added_at": item["added_at"],
                    "part": part  # Nested part data
                })
        
        # Calculate total
        total_cents = sum(
            (item["part"].get("price_cents") or 0) * item["quantity"]
            for item in items if item.get("part")
        )
        
        return {
            "id": cart_id,
            "items": items,
            "totalCents": total_cents,
            "itemCount": sum(item["quantity"] for item in items)
        }
        
    except Exception as e:
        logger.error("Get cart failed", cart_id=cart_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get cart")
