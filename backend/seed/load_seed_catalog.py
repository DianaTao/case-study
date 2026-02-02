"""Load seed catalog parts derived from PartSelect URLs."""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db
import structlog

logger = structlog.get_logger()

SEED_FILE = Path(__file__).parent / "seed_parts.json"


def normalize_partselect_url(url: str) -> str:
    """Strip query params and keep canonical .htm URL."""
    parsed = urlparse(url)
    if parsed.path.endswith(".htm"):
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return url


def load_seed_catalog() -> None:
    """Load seed catalog into parts table (no scraping)."""
    if not SEED_FILE.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_FILE}")

    with SEED_FILE.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    parts = payload.get("parts", [])
    if not parts:
        logger.warning("No parts in seed file", file=str(SEED_FILE))
        return

    db = get_db()
    inserted = 0
    updated = 0
    symptoms_inserted = 0

    for item in parts:
        canonical_url = normalize_partselect_url(item.get("canonical_url", ""))
        troubleshooting_symptoms = item.get("troubleshooting_symptoms", [])
        
        part_data = {
            "appliance_type": item.get("appliance_type"),
            "partselect_number": item.get("partselect_number"),
            "manufacturer_number": item.get("manufacturer_part_number"),
            "name": item.get("title"),
            "brand": item.get("brand"),
            "product_url": canonical_url,
            "canonical_url": canonical_url,
            "manufactured_by": item.get("manufactured_by"),
            "troubleshooting_symptoms": troubleshooting_symptoms,
        }

        if "price_cents" in item:
            part_data["price_cents"] = item.get("price_cents")
        if "stock_status" in item:
            part_data["stock_status"] = item.get("stock_status")
        if "image_url" in item:
            part_data["image_url"] = item.get("image_url")

        # Insert or update
        existing = db.table("parts").select("id").eq(
            "partselect_number", part_data["partselect_number"]
        ).execute()

        if existing.data:
            db.table("parts").update(part_data).eq(
                "partselect_number", part_data["partselect_number"]
            ).execute()
            updated += 1
        else:
            db.table("parts").insert(part_data).execute()
            inserted += 1
        
        # Handle symptom mappings
        if troubleshooting_symptoms:
            # Delete existing symptoms for this part
            db.table("part_symptoms").delete().eq(
                "partselect_number", part_data["partselect_number"]
            ).execute()
            
            # Insert new symptoms
            symptom_rows = [
                {
                    "partselect_number": part_data["partselect_number"],
                    "symptom": symptom.strip()
                }
                for symptom in troubleshooting_symptoms
                if symptom and symptom.strip()
            ]
            
            if symptom_rows:
                db.table("part_symptoms").insert(symptom_rows).execute()
                symptoms_inserted += len(symptom_rows)

    logger.info("Seed catalog loaded", inserted=inserted, updated=updated, symptoms=symptoms_inserted, total=len(parts))
    print(f"✅ Seed catalog loaded: {inserted} inserted, {updated} updated, {symptoms_inserted} symptoms, {len(parts)} total")


if __name__ == "__main__":
    load_seed_catalog()
