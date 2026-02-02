"""Compatibility checking API."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import Optional
import structlog

from database import get_db

logger = structlog.get_logger()
router = APIRouter()


class CompatibilityRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())  # Allow model_number field
    
    partselect_number: str
    model_number: str


class CompatibilityResponse(BaseModel):
    status: str  # fits | no_fit | need_info
    confidence: str  # exact | likely | unknown
    reason: str
    evidence_url: Optional[str] = None
    evidence_snippet: Optional[str] = None


@router.post("/", response_model=CompatibilityResponse)
async def check_compatibility(request: CompatibilityRequest):
    """
    Check if a part is compatible with a model.
    
    This is a deterministic check based on scraped compatibility data.
    We ONLY return 'fits' if we have exact data from model pages.
    """
    try:
        # Validate input
        if not request.partselect_number or not request.model_number:
            raise HTTPException(
                status_code=400, 
                detail="Both partselect_number and model_number are required"
            )
        
        db = get_db()
        
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Database connection unavailable"
            )
        
        # Normalize model number (uppercase, remove spaces/dashes)
        normalized_model = request.model_number.upper().replace(" ", "").replace("-", "")
        
        # Query compatibility table
        result = db.table("model_parts").select("*").eq(
            "partselect_number", request.partselect_number
        ).eq("model_number", normalized_model).execute()
        
        if result.data and len(result.data) > 0:
            # Found compatibility record
            record = result.data[0]
            
            if record["confidence"] == "exact":
                return CompatibilityResponse(
                    status="fits",
                    confidence="exact",
                    reason=f"This part is confirmed compatible with model {request.model_number}.",
                    evidence_url=record.get("evidence_url"),
                    evidence_snippet=record.get("evidence_snippet"),
                )
            else:
                return CompatibilityResponse(
                    status="need_info",
                    confidence=record["confidence"],
                    reason=f"Compatibility with model {request.model_number} is uncertain. We recommend verifying on PartSelect.com.",
                    evidence_url=record.get("evidence_url"),
                    evidence_snippet=record.get("evidence_snippet"),
                )
        else:
            # No record found - check if part and model exist
            part_result = db.table("parts").select("appliance_type").eq(
                "partselect_number", request.partselect_number
            ).execute()
            
            model_result = db.table("models").select("appliance_type").eq(
                "model_number", normalized_model
            ).execute()
            
            # If different appliance types, definitely doesn't fit
            if (part_result.data and model_result.data and 
                part_result.data[0]["appliance_type"] != model_result.data[0]["appliance_type"]):
                return CompatibilityResponse(
                    status="no_fit",
                    confidence="exact",
                    reason=f"This part is for a different appliance type and won't fit model {request.model_number}.",
                )
            
            # Otherwise, we don't have compatibility data
            return CompatibilityResponse(
                status="need_info",
                confidence="unknown",
                reason=f"We don't have compatibility data for part {request.partselect_number} with model {request.model_number}. Please verify the model number or check PartSelect.com directly.",
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "Compatibility check failed", 
            part=request.partselect_number, 
            model=request.model_number, 
            error=str(e),
            error_type=type(e).__name__
        )
        # Return a more helpful error message
        raise HTTPException(
            status_code=500, 
            detail=f"Compatibility check failed: {str(e)}"
        )
