"""Compatibility checking using Playwright and OpenAI."""
from __future__ import annotations

import re
from typing import Optional, Dict, List
from playwright.async_api import async_playwright
import openai
from config import settings


async def check_part_compatibility(
    product_url: str,
    part_number: str,
    manufacturer_part: str,
    user_model: str
) -> Dict[str, any]:
    """
    Check if a part is compatible with a user's model by:
    1. Scraping "replaces these" part numbers from PartSelect
    2. Scraping "works with" appliance/model info
    3. Using OpenAI to determine compatibility
    
    Args:
        product_url: PartSelect product page URL
        part_number: PartSelect number (e.g., "PS11752778")
        manufacturer_part: Manufacturer part number (e.g., "WPW10321304")
        user_model: User's model number (e.g., "WDT780SAEM1")
    
    Returns:
        {
            "compatible": bool,  # True/False/None (unknown)
            "confidence": str,  # "high", "medium", "low", "unknown"
            "reason": str,  # Explanation
            "replaces": List[str],  # Replacement part numbers found
            "works_with": str,  # "Refrigerator", "Dishwasher", etc.
        }
    """
    print(f"\n{'='*70}")
    print(f"🔍 CHECKING COMPATIBILITY")
    print(f"{'='*70}")
    print(f"URL: {product_url}")
    print(f"Part: {part_number} ({manufacturer_part})")
    print(f"User Model: {user_model}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        try:
            print(f"📡 Loading page...")
            await page.goto(product_url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2000)  # Allow JS to render
            print(f"✅ Page loaded\n")
            
            extracted_data = {}
            
            # 1. Extract "replaces these" part numbers
            print(f"🔎 Step 1: Extracting replacement part numbers...")
            replaces_parts = await _extract_replaces_parts(page)
            extracted_data["replaces"] = replaces_parts
            if replaces_parts:
                print(f"   ✅ Found {len(replaces_parts)} replacement part numbers")
                print(f"   Parts: {', '.join(replaces_parts[:5])}...")
            else:
                print(f"   ❌ No replacement parts found")
            
            # 2. Extract "works with" information
            print(f"\n🔎 Step 2: Extracting 'works with' information...")
            works_with = await _extract_works_with(page)
            extracted_data["works_with"] = works_with
            if works_with:
                print(f"   ✅ Found: {works_with}")
            else:
                print(f"   ❌ No 'works with' info found")
            
            # 3. Extract compatible models (if explicitly listed)
            print(f"\n🔎 Step 3: Extracting compatible models...")
            compatible_models = await _extract_compatible_models(page)
            extracted_data["compatible_models"] = compatible_models
            if compatible_models:
                print(f"   ✅ Found {len(compatible_models)} compatible models")
            else:
                print(f"   ❌ No explicit model list found")
            
            print(f"\n{'='*70}")
            print(f"📊 EXTRACTION COMPLETE")
            print(f"{'='*70}")
            print(f"Replaces: {len(replaces_parts)} parts")
            print(f"Works with: {works_with or 'N/A'}")
            print(f"Compatible models: {len(compatible_models)} models")
            print(f"{'='*70}\n")
            
            # 4. Use OpenAI to determine compatibility
            result = await _check_compatibility_with_openai(
                extracted_data=extracted_data,
                part_number=part_number,
                manufacturer_part=manufacturer_part,
                user_model=user_model
            )
            
            return result
                
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
            return {
                "compatible": None,
                "confidence": "unknown",
                "reason": "Unable to verify compatibility. Please check PartSelect directly.",
                "replaces": [],
                "works_with": None
            }
        finally:
            await browser.close()


async def _extract_replaces_parts(page) -> List[str]:
    """
    Extract all part numbers from 'Part# XXX replaces these:' style sections.

    This is tuned for PartSelect's copy like:
      "Part# WPW10321304 replaces these: AP6019471, 2171046, ..."
    """
    try:
        replaces_text = await page.evaluate(
            """
            () => {
                if (!document.body) return null;
                const text = document.body.innerText || '';
                const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);

                // Strategy 1: Look for explicit "Part#" + "replaces these"
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    const lower = line.toLowerCase();

                    if (lower.includes('part#') && lower.includes('replaces these')) {
                        // Collect this line and a few following lines in case the list wraps
                        let content = [];
                        for (let j = i; j < Math.min(i + 4, lines.length); j++) {
                            content.push(lines[j]);
                            // Stop early if we hit an empty separator line
                            if (!lines[j].trim()) break;
                        }
                        return content.join(' ');
                    }
                }

                // Strategy 2: Fallback – any "replaces these:" line
                for (let i = 0; i < lines.length; i++) {
                    const lower = lines[i].toLowerCase();
                    if (lower.includes('replaces these:') || lower.includes('replaces these')) {
                        let content = [];
                        for (let j = i; j < Math.min(i + 4, lines.length); j++) {
                            content.push(lines[j]);
                            if (!lines[j].trim()) break;
                        }
                        return content.join(' ');
                    }
                }

                return null;
            }
            """
        )

        if not replaces_text:
            return []

        # Extract part numbers (various formats)
        # Common formats: AP6019471, 2171046, W10321302, WPW10321304VP
        part_numbers: list[str] = []

        # Pattern 1: AP + digits (e.g., AP6019471)
        ap_parts = re.findall(r"\bAP\d{6,9}\b", replaces_text, re.IGNORECASE)
        part_numbers.extend(ap_parts)

        # Pattern 2: W* + digits + optional letters (e.g., W10321302, WPW10321304VP)
        w_parts = re.findall(r"\bW\w*\d{5,}\w*\b", replaces_text, re.IGNORECASE)
        part_numbers.extend(w_parts)

        # Pattern 3: Pure digits (7-10 digits, e.g., 2171046)
        digit_parts = re.findall(r"\b\d{6,10}[A-Z]?\b", replaces_text)
        part_numbers.extend(digit_parts)

        # Pattern 4: Mixed alphanumeric (e.g., 2179607K, 2304235K)
        mixed_parts = re.findall(r"\b\d{6,9}[A-Z]{1,3}\b", replaces_text)
        part_numbers.extend(mixed_parts)

        # Deduplicate while preserving order
        seen = set()
        unique_parts: list[str] = []
        for p in part_numbers:
            part_upper = p.upper()
            if part_upper not in seen:
                seen.add(part_upper)
                unique_parts.append(part_upper)

        return unique_parts

    except Exception as e:
        print(f"   Error extracting replaces parts: {e}")
        return []


async def _extract_works_with(page) -> Optional[str]:
    """Extract 'works with' appliance types (e.g., 'Refrigerator', 'Dishwasher')."""
    try:
        works_with_text = await page.evaluate("""
            () => {
                const text = document.body.innerText;
                const lines = text.split('\\n');
                
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    const lower = line.toLowerCase();
                    
                    if (lower.includes('works with') || lower.includes('this part works with')) {
                        // Get next few lines
                        let content = [];
                        for (let j = i; j < Math.min(i + 3, lines.length); j++) {
                            content.push(lines[j]);
                        }
                        return content.join(' ');
                    }
                }
                
                return null;
            }
        """)
        
        if not works_with_text:
            return None
        
        # Extract appliance types
        lower = works_with_text.lower()
        if 'refrigerator' in lower:
            return "Refrigerator"
        elif 'dishwasher' in lower:
            return "Dishwasher"
        elif 'fridge' in lower:
            return "Refrigerator"
        
        return works_with_text[:100]  # Return raw text if no specific match
        
    except Exception as e:
        print(f"   Error extracting works with: {e}")
        return None


async def _extract_compatible_models(page) -> List[str]:
    """Extract explicit model numbers if listed on the page."""
    try:
        # Look for model numbers in the page text
        page_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
        
        if not page_text:
            return []
        
        # Common model number patterns for Whirlpool/Maytag/etc
        # e.g., WDT780SAEM1, WRF555SDFZ, MDB4949SDZ
        model_pattern = r'\b[A-Z]{2,4}\d{3,4}[A-Z]{2,5}\d?\b'
        models = re.findall(model_pattern, page_text)
        
        # Filter out obvious non-models (like part numbers)
        filtered = []
        for model in models:
            # Skip if it looks like a part number (starts with PS, AP, W10, etc.)
            if model.startswith(('PS', 'AP', 'W10', 'WP')):
                continue
            filtered.append(model)
        
        # Deduplicate
        return list(set(filtered))[:20]  # Limit to 20 models
        
    except Exception as e:
        print(f"   Error extracting models: {e}")
        return []


async def _check_compatibility_with_openai(
    extracted_data: Dict,
    part_number: str,
    manufacturer_part: str,
    user_model: str
) -> Dict[str, any]:
    """Use OpenAI to determine compatibility based on extracted data."""
    print(f"🤖 Using OpenAI to check compatibility...")
    
    # Build context
    context_parts = []
    
    replaces = extracted_data.get("replaces", [])
    if replaces:
        context_parts.append(f"**Replacement Part Numbers:**\n{', '.join(replaces)}")
    
    works_with = extracted_data.get("works_with")
    if works_with:
        context_parts.append(f"**Works With:**\n{works_with}")
    
    compatible_models = extracted_data.get("compatible_models", [])
    if compatible_models:
        context_parts.append(f"**Compatible Models Found:**\n{', '.join(compatible_models[:10])}")
    
    context = "\n\n".join(context_parts) if context_parts else "(No compatibility data extracted from page)"
    
    # OpenAI prompt
    prompt = f"""You are a helpful assistant checking appliance part compatibility.

Part Information:
- PartSelect Number: {part_number}
- Manufacturer Part Number: {manufacturer_part}
- User's Model Number: {user_model}

Extracted Compatibility Data from PartSelect:
{context}

Task:
Determine if this part is compatible with the user's model number "{user_model}".

Compatibility Rules:
1. **EXACT MATCH**: If user's model number appears in "Compatible Models Found" → Compatible (high confidence)
2. **REPLACEMENT MATCH**: If user's model is a variant of the manufacturer part or appears in replacement list → Compatible (medium confidence)
3. **APPLIANCE MISMATCH**: If user's model is for a different appliance type (e.g., dishwasher model but part is for refrigerator) → Not Compatible (high confidence)
4. **NO DATA**: If no compatibility data available → Unknown (low confidence)

Model Number Analysis:
- User model: {user_model}
- First 3-4 letters indicate brand/appliance (e.g., WDT = Whirlpool Dishwasher, WRF = Whirlpool Refrigerator)
- Compare with "Works With" appliance type

Respond in EXACTLY this JSON format:
{{
  "compatible": true/false/null,
  "confidence": "high" or "medium" or "low" or "unknown",
  "reason": "Clear explanation in 1-2 sentences"
}}

Example responses:
- If model matches: {{"compatible": true, "confidence": "high", "reason": "Model {user_model} found in compatible models list."}}
- If appliance mismatch: {{"compatible": false, "confidence": "high", "reason": "Part is for Refrigerator but model {user_model} appears to be a Dishwasher (WDT prefix)."}}
- If no data: {{"compatible": null, "confidence": "unknown", "reason": "No compatibility data available. Please verify on PartSelect."}}

Your response (JSON only):"""

    try:
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for appliance part compatibility. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Very low for factual responses
            max_tokens=300
        )
        
        result_text = response.choices[0].message.content.strip()
        print(f"✅ OpenAI response received")
        
        # Parse JSON response
        import json
        
        # Handle markdown code blocks if present
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(result_text)
        
        # Add extracted data to result
        result["replaces"] = replaces
        result["works_with"] = works_with
        
        print(f"✅ Compatible: {result['compatible']} (confidence: {result['confidence']})")
        print(f"   Reason: {result['reason']}")
        
        return result
        
    except Exception as e:
        print(f"❌ OpenAI API failed: {e}")
        return {
            "compatible": None,
            "confidence": "unknown",
            "reason": "Unable to verify compatibility. Please check PartSelect directly.",
            "replaces": replaces,
            "works_with": works_with
        }
