"""Scrape parts from a PartSelect model page.

This is a more reliable compatibility check - we check if a part is listed
on the model's page rather than trying to infer from the part page.
"""
from typing import List, Dict, Optional
from playwright.async_api import async_playwright
import re


async def get_parts_for_model(model_number: str) -> Dict[str, any]:
    """
    Scrape all parts listed for a specific model from PartSelect.
    
    Args:
        model_number: Model number (e.g., "WDT780SAEM1")
    
    Returns:
        {
            "model_number": str,
            "model_url": str,
            "parts": List[Dict],  # List of parts with PS numbers
            "total_parts": int,
            "success": bool
        }
    """
    model_url = f"https://www.partselect.com/Models/{model_number}"
    
    print(f"\n🔍 Scraping parts for model {model_number}")
    print(f"   URL: {model_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        try:
            print(f"📡 Loading model page...")
            await page.goto(model_url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)  # Allow JS to render parts list
            
            # Scroll to load more parts if needed (lazy loading)
            print(f"📜 Scrolling to load all parts...")
            await _scroll_to_load_parts(page)
            
            print(f"✅ Page loaded, extracting parts...")
            
            # Extract all PartSelect numbers from the page
            parts = await _extract_parts_from_model_page(page)
            
            print(f"✅ Found {len(parts)} parts for model {model_number}")
            
            return {
                "model_number": model_number,
                "model_url": model_url,
                "parts": parts,
                "total_parts": len(parts),
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Failed to scrape model page: {e}")
            return {
                "model_number": model_number,
                "model_url": model_url,
                "parts": [],
                "total_parts": 0,
                "success": False,
                "error": str(e)
            }
        finally:
            await browser.close()


async def _scroll_to_load_parts(page) -> None:
    """Scroll down to trigger lazy loading of parts."""
    try:
        # Scroll down multiple times to load all parts
        for i in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)  # Wait for lazy load
            
            # Check if we've reached the bottom
            is_at_bottom = await page.evaluate("""
                () => {
                    return (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 100;
                }
            """)
            
            if is_at_bottom:
                break
    except Exception as e:
        print(f"   ⚠️  Scroll error (non-fatal): {e}")


async def _extract_parts_from_model_page(page) -> List[Dict[str, str]]:
    """
    Extract all PartSelect numbers and related info from the model page.
    
    Looks for patterns like:
    - "PartSelect #: PS3406971"
    - Links containing "/PS3406971"
    """
    try:
        parts_data = await page.evaluate("""
            () => {
                const parts = [];
                const bodyText = document.body.innerText || '';
                const bodyHTML = document.body.innerHTML || '';
                
                // Strategy 1: Find "PartSelect #: PS####" patterns in text
                const psNumberPattern = /PartSelect\\s*#:?\\s*PS(\\d{6,9})/gi;
                let match;
                const foundPSNumbers = new Set();
                
                while ((match = psNumberPattern.exec(bodyText)) !== null) {
                    const psNumber = 'PS' + match[1];
                    foundPSNumbers.add(psNumber);
                }
                
                // Strategy 2: Find links containing /PS####
                const links = document.querySelectorAll('a[href*="/PS"]');
                links.forEach(link => {
                    const href = link.getAttribute('href') || '';
                    const psMatch = href.match(/\\/PS(\\d{6,9})/);
                    if (psMatch) {
                        foundPSNumbers.add('PS' + psMatch[1]);
                    }
                });
                
                // Strategy 3: Find any text containing PS#### pattern
                const allPSMatches = bodyText.match(/PS\\d{6,9}/g);
                if (allPSMatches) {
                    allPSMatches.forEach(ps => foundPSNumbers.add(ps));
                }
                
                // Convert to array and extract additional info if available
                Array.from(foundPSNumbers).forEach(psNumber => {
                    // Try to find part name near the PS number
                    const psIndex = bodyText.indexOf(psNumber);
                    if (psIndex !== -1) {
                        // Get surrounding text (100 chars before and after)
                        const start = Math.max(0, psIndex - 100);
                        const end = Math.min(bodyText.length, psIndex + 100);
                        const context = bodyText.substring(start, end);
                        
                        // Try to extract part name (usually before the PS number)
                        const beforePS = context.substring(0, context.indexOf(psNumber));
                        const lines = beforePS.split('\\n').filter(l => l.trim());
                        const partName = lines.length > 0 ? lines[lines.length - 1].trim() : null;
                        
                        parts.push({
                            partselectNumber: psNumber,
                            name: partName || 'Unknown Part',
                            foundInContext: context.substring(0, 50) + '...'
                        });
                    } else {
                        parts.push({
                            partselectNumber: psNumber,
                            name: 'Unknown Part',
                            foundInContext: null
                        });
                    }
                });
                
                return parts;
            }
        """)
        
        # Deduplicate by PartSelect number
        seen = set()
        unique_parts = []
        for part in parts_data:
            ps_num = part.get("partselectNumber", "").upper()
            if ps_num and ps_num not in seen:
                seen.add(ps_num)
                unique_parts.append({
                    "partselect_number": ps_num,
                    "name": part.get("name", "Unknown Part"),
                })
        
        return unique_parts
        
    except Exception as e:
        print(f"   ❌ Error extracting parts: {e}")
        return []


async def check_part_in_model_list(partselect_number: str, model_number: str) -> Dict[str, any]:
    """
    Check if a specific part is listed on a model's page.
    
    This is the most reliable compatibility check - if the part appears
    on the model page, it's definitely compatible.
    
    Args:
        partselect_number: PartSelect number (e.g., "PS3406971")
        model_number: Model number (e.g., "WDT780SAEM1")
    
    Returns:
        {
            "is_listed": bool,
            "model_url": str,
            "confidence": str,  # "exact" if found, "unknown" if not
            "total_parts_on_model": int
        }
    """
    result = await get_parts_for_model(model_number)
    
    if not result["success"]:
        return {
            "is_listed": False,
            "model_url": result["model_url"],
            "confidence": "unknown",
            "total_parts_on_model": 0,
            "error": result.get("error")
        }
    
    parts = result["parts"]
    part_numbers = [p["partselect_number"].upper() for p in parts]
    partselect_upper = partselect_number.upper()
    
    is_listed = partselect_upper in part_numbers
    
    return {
        "is_listed": is_listed,
        "model_url": result["model_url"],
        "confidence": "exact" if is_listed else "unknown",
        "total_parts_on_model": len(parts),
        "found_parts": parts[:10] if not is_listed else None  # Show sample if not found
    }
