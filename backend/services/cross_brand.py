"""
Cross-brand compatibility checking for appliance parts.

Many appliance brands are manufactured by the same parent company,
meaning parts are often interchangeable. This module handles those mappings.
"""

import re
from typing import Dict, Any, Optional


# Cross-brand manufacturing relationships
CROSS_BRAND_MAPPING = {
    "kenmore": {
        "parent_manufacturer": "whirlpool",
        "prefix_rules": {
            # Kenmore refrigerators starting with these prefixes are Whirlpool-made
            r'^253': 'whirlpool',  # Refrigerators
            r'^596': 'whirlpool',  # Refrigerators
            r'^795': 'lg',         # Refrigerators (LG-made)
            r'^665': 'whirlpool',  # Dishwashers
            r'^630': 'whirlpool',  # Dishwashers
        },
        "confidence": 0.85
    },
    "kitchenaid": {
        "parent_manufacturer": "whirlpool",
        "prefix_rules": {},
        "confidence": 0.95  # KitchenAid is wholly owned by Whirlpool
    },
    "maytag": {
        "parent_manufacturer": "whirlpool",
        "prefix_rules": {},
        "confidence": 0.90
    },
    "amana": {
        "parent_manufacturer": "whirlpool",
        "prefix_rules": {},
        "confidence": 0.90
    },
    "jenn-air": {
        "parent_manufacturer": "whirlpool",
        "prefix_rules": {},
        "confidence": 0.95
    },
    "roper": {
        "parent_manufacturer": "whirlpool",
        "prefix_rules": {},
        "confidence": 0.85
    }
}


async def check_cross_brand_compatibility(
    part_brand: str, 
    model_number: str, 
    detected_brand: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check if a part fits due to cross-brand manufacturing relationships.
    
    Args:
        part_brand: Brand of the part (e.g., "Whirlpool")
        model_number: Full model number (e.g., "25377202792")
        detected_brand: Brand mentioned by user (e.g., "Kenmore")
    
    Returns:
        {
            "is_compatible": True/False/None,
            "reason": "explanation",
            "confidence": 0.0-1.0
        }
    """
    if not detected_brand:
        return {
            "is_compatible": None,
            "reason": "No model brand detected",
            "confidence": 0.0
        }
    
    model_brand_lower = detected_brand.lower().strip()
    part_brand_lower = part_brand.lower().strip()
    
    # Direct match - no cross-brand needed
    if model_brand_lower == part_brand_lower:
        return {
            "is_compatible": True,
            "reason": f"Direct brand match: {detected_brand}",
            "confidence": 1.0
        }
    
    # Check if model brand has cross-brand relationships
    if model_brand_lower not in CROSS_BRAND_MAPPING:
        return {
            "is_compatible": None,
            "reason": f"No cross-brand data for {detected_brand}",
            "confidence": 0.0
        }
    
    brand_info = CROSS_BRAND_MAPPING[model_brand_lower]
    parent = brand_info["parent_manufacturer"]
    
    # Check if part is from the parent manufacturer
    if parent == part_brand_lower:
        # Check prefix rules if they exist
        prefix_rules = brand_info.get("prefix_rules", {})
        
        if prefix_rules:
            # Model number must match a prefix rule
            for pattern, manufacturer in prefix_rules.items():
                if re.match(pattern, model_number):
                    if manufacturer == part_brand_lower:
                        return {
                            "is_compatible": True,
                            "reason": (
                                f"Your {detected_brand} model {model_number} is manufactured by {part_brand.title()}. "
                                f"This {part_brand.title()} part should be compatible."
                            ),
                            "confidence": brand_info["confidence"]
                        }
                    else:
                        return {
                            "is_compatible": False,
                            "reason": (
                                f"Your {detected_brand} model {model_number} appears to be manufactured by {manufacturer.title()}, "
                                f"not {part_brand.title()}."
                            ),
                            "confidence": brand_info["confidence"]
                        }
            
            # No prefix match - uncertain
            return {
                "is_compatible": None,
                "reason": (
                    f"Cannot determine if your {detected_brand} model {model_number} "
                    f"is compatible with {part_brand.title()} parts. Please verify on PartSelect."
                ),
                "confidence": 0.3
            }
        else:
            # No prefix rules - assume compatible if parent matches
            return {
                "is_compatible": True,
                "reason": (
                    f"{detected_brand} appliances are manufactured by {parent.title()}. "
                    f"This {part_brand.title()} part should be compatible."
                ),
                "confidence": brand_info["confidence"]
            }
    
    # Part brand doesn't match parent
    return {
        "is_compatible": None,
        "reason": f"No cross-brand relationship found between {detected_brand} and {part_brand}",
        "confidence": 0.0
    }


def get_supported_cross_brands() -> list[str]:
    """Return list of brands with cross-brand support."""
    return list(CROSS_BRAND_MAPPING.keys())
