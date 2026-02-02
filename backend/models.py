"""Pydantic models for API."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Part(BaseModel):
    """Part model."""
    id: Optional[str] = None
    appliance_type: str
    partselect_number: str
    manufacturer_number: Optional[str] = None
    name: str
    brand: Optional[str] = None
    price_cents: Optional[int] = None
    stock_status: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    canonical_url: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[float] = None
    review_count: int = 0
    has_install_instructions: bool = False
    has_videos: bool = False
    install_links: List[str] = []
    install_summary: Optional[str] = None
    common_symptoms: List[str] = []
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Model(BaseModel):
    """Model model."""
    id: Optional[str] = None
    appliance_type: str
    model_number: str
    brand: Optional[str] = None
    model_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Chat request."""
    session_id: str
    message: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    """Chat response with versioning and metadata."""
    version: str = "1.1"
    assistant_text: str
    intent: Optional[str] = None
    source: Optional[str] = None  # 'db' | 'scraper+llm' | 'rules' | 'mixed'
    cards: List[dict] = []
    quick_replies: List[str] = []
    events: List[dict] = []
