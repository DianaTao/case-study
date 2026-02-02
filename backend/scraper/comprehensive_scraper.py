#!/usr/bin/env python3
"""
PartSelect comprehensive product-page scraper (Playwright DOM/JSON-LD extraction)

Extracts:
- price_cents (int)
- stock_status: in_stock | out_of_stock | backorder | unknown
- manufactured_by (string)
- troubleshooting_symptoms (list[str]) from "This part fixes the following symptoms:"
- image_url

Usage:
    python comprehensive_scraper.py --input parts_seed.json --output parts_enriched.json --headless
"""

import argparse
import json
import re
import time
from typing import Any, Dict, List, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# -----------------------------
# Helpers
# -----------------------------

PRICE_RE = re.compile(r"(\d[\d,]*)(\.\d{1,2})?")
SCHEMA_INSTOCK = re.compile(r"instock", re.I)
SCHEMA_OUTOFSTOCK = re.compile(r"outofstock", re.I)
SCHEMA_BACKORDER = re.compile(r"backorder", re.I)

def to_cents(price_str: Optional[str]) -> Optional[int]:
    if not price_str:
        return None
    s = price_str.strip()
    s = s.replace("$", "").replace("USD", "").strip()
    m = PRICE_RE.search(s)
    if not m:
        return None
    whole = m.group(1).replace(",", "")
    frac = m.group(2) or ".00"
    try:
        val = float(f"{whole}{frac}")
        return int(round(val * 100))
    except ValueError:
        return None

def normalize_stock(text: Optional[str]) -> str:
    if not text:
        return "unknown"
    t = text.strip().lower()

    if SCHEMA_INSTOCK.search(t):
        return "in_stock"
    if SCHEMA_OUTOFSTOCK.search(t):
        return "out_of_stock"
    if SCHEMA_BACKORDER.search(t):
        return "backorder"

    if "in stock" in t:
        return "in_stock"
    if "out of stock" in t:
        return "out_of_stock"
    if "backorder" in t or "back order" in t:
        return "backorder"

    return "unknown"

def clean_text(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return re.sub(r"\s+", " ", s).strip() or None


# -----------------------------
# Extraction: JSON-LD
# -----------------------------

def extract_jsonld_product(page) -> Dict[str, Any]:
    """
    Tries to find Product JSON-LD and returns:
      { price: str|None, availability: str|None, name: str|None, image: str|None }
    """
    scripts = page.query_selector_all('script[type="application/ld+json"]')
    raw_jsons = []
    for sc in scripts:
        txt = sc.inner_text().strip()
        if txt:
            raw_jsons.append(txt)

    def iter_candidates(obj: Any):
        if isinstance(obj, list):
            for x in obj:
                yield from iter_candidates(x)
        elif isinstance(obj, dict):
            if "@graph" in obj and isinstance(obj["@graph"], list):
                for x in obj["@graph"]:
                    yield x
            yield obj

    for raw in raw_jsons:
        try:
            parsed = json.loads(raw)
        except Exception:
            continue

        for cand in iter_candidates(parsed):
            if not isinstance(cand, dict):
                continue

            typ = str(cand.get("@type", "")).lower()
            if typ == "product" or ("offers" in cand and "name" in cand):
                offers = cand.get("offers")
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                if not isinstance(offers, dict):
                    offers = {}

                price = offers.get("price")
                availability = offers.get("availability")
                name = cand.get("name")
                image = cand.get("image")
                if isinstance(image, list) and image:
                    image = image[0]

                return {
                    "price": str(price) if price is not None else None,
                    "availability": str(availability) if availability is not None else None,
                    "name": str(name) if name is not None else None,
                    "image": str(image) if image is not None else None,
                }

    return {"price": None, "availability": None, "name": None, "image": None}


# -----------------------------
# Extraction: DOM fallbacks
# -----------------------------

def extract_price_dom(page) -> Optional[str]:
    """Generic fallback: scan visible text for a $xx.xx-like pattern."""
    selector_candidates = [
        '[data-testid*="price"]',
        '[class*="price"]',
        'text=/\\$\\s*\\d[\\d,]*(\\.\\d{2})?/',
    ]
    for sel in selector_candidates:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                txt = clean_text(loc.inner_text())
                if txt and "$" in txt:
                    return txt
        except Exception:
            continue

    try:
        body_text = page.evaluate("() => document.body ? document.body.innerText : ''")
        if not body_text:
            return None
        m = re.search(r"\$\s*\d[\d,]*(\.\d{2})?", body_text)
        return m.group(0) if m else None
    except Exception:
        return None

def extract_stock_dom(page) -> Optional[str]:
    """Generic fallback: look for common stock phrases in the page text."""
    try:
        body_text = page.evaluate("() => document.body ? document.body.innerText : ''")
        if not body_text:
            return None
        t = body_text.lower()
        if "in stock" in t:
            return "In Stock"
        if "out of stock" in t:
            return "Out of Stock"
        if "backorder" in t or "back order" in t:
            return "Backorder"
        return None
    except Exception:
        return None

def extract_manufactured_by(page) -> Optional[str]:
    """Heuristic: find the line that contains 'Manufactured by'"""
    try:
        body_text = page.evaluate("() => document.body ? document.body.innerText : ''")
        if not body_text:
            return None
        for line in body_text.splitlines():
            if "manufactured by" in line.lower():
                return clean_text(line)
        return None
    except Exception:
        return None

def extract_troubleshooting_symptoms(page) -> List[str]:
    """
    Tries to scroll to "Troubleshooting" section and extract the symptoms listed under:
    "This part fixes the following symptoms:"
    Returns [] if not found.
    """
    symptoms: List[str] = []

    try:
        tloc = page.locator("text=Troubleshooting").first
        if tloc.count() > 0:
            tloc.scroll_into_view_if_needed()
            page.wait_for_timeout(600)
    except Exception:
        pass

    try:
        body_text = page.evaluate("() => document.body ? document.body.innerText : ''")
        if not body_text:
            return []

        marker = "this part fixes the following symptoms"
        lower = body_text.lower()
        idx = lower.find(marker)
        if idx == -1:
            return []

        # Take a window after marker
        window = body_text[idx: idx + 1200]
        lines = [clean_text(x) for x in window.splitlines()]
        lines = [x for x in lines if x]

        # After the marker line, subsequent lines are symptom items
        started = False
        for line in lines:
            if marker in line.lower():
                started = True
                continue
            if not started:
                continue

            # Stop at new sections
            if line.lower() in {"questions and answers", "customer questions and answers", "reviews", "installation instructions", "product description", "videos"}:
                break

            # Filter out noise
            if len(line) < 3:
                continue
            if "$" in line:
                continue
            if re.search(r"[A-Za-z]", line):
                symptoms.append(line)

            if len(symptoms) >= 20:
                break

        # De-dup
        seen = set()
        out = []
        for s in symptoms:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    except Exception:
        return []


# -----------------------------
# Scrape one URL
# -----------------------------

def scrape_one(page, part: Dict[str, Any]) -> Dict[str, Any]:
    url = part["canonical_url"]
    print(f"\n{'='*60}")
    print(f"🔍 Scraping: {url}")
    print(f"{'='*60}")
    
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1200)

    # 1) JSON-LD primary
    print("🔎 Step 1: Extracting JSON-LD...")
    ld = extract_jsonld_product(page)
    price_cents = to_cents(ld.get("price"))
    stock_status = normalize_stock(ld.get("availability"))
    image_url = ld.get("image")
    
    print(f"   JSON-LD: price={price_cents}, stock={stock_status}, image={image_url is not None}")

    # 2) DOM fallback
    if price_cents is None:
        print("🔎 Step 2: DOM price fallback...")
        price_text = extract_price_dom(page)
        price_cents = to_cents(price_text)
        print(f"   DOM price: {price_cents}")
        
    if stock_status == "unknown":
        print("🔎 Step 3: DOM stock fallback...")
        stock_text = extract_stock_dom(page)
        stock_status = normalize_stock(stock_text)
        print(f"   DOM stock: {stock_status}")

    # 3) Enrichments
    print("🔎 Step 4: Extracting manufactured_by...")
    manufactured_by = extract_manufactured_by(page)
    print(f"   Manufactured by: {manufactured_by}")
    
    print("🔎 Step 5: Extracting troubleshooting symptoms...")
    troubleshooting = extract_troubleshooting_symptoms(page)
    print(f"   Found {len(troubleshooting)} symptoms:")
    for s in troubleshooting[:5]:  # Show first 5
        print(f"     - {s}")
    if len(troubleshooting) > 5:
        print(f"     ... and {len(troubleshooting) - 5} more")

    part = dict(part)
    part["price_cents"] = price_cents
    part["stock_status"] = stock_status
    part["manufactured_by"] = manufactured_by
    part["troubleshooting_symptoms"] = troubleshooting
    part["image_url"] = image_url or part.get("image_url")
    
    print(f"\n✅ Complete: price=${price_cents/100:.2f if price_cents else 'N/A'}, stock={stock_status}, symptoms={len(troubleshooting)}")
    
    return part


# -----------------------------
# Main
# -----------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to parts_seed.json")
    ap.add_argument("--output", required=True, help="Path to write enriched JSON")
    ap.add_argument("--headless", action="store_true", help="Run browser headless")
    ap.add_argument("--delay_ms", type=int, default=1200, help="Delay between requests (polite rate limiting)")
    ap.add_argument("--retries", type=int, default=1, help="Retries per URL on failure")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    parts: List[Dict[str, Any]] = data.get("parts", [])
    if not parts:
        raise SystemExit("Input JSON has no 'parts' array.")

    enriched: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        for idx, part in enumerate(parts, start=1):
            url = part.get("canonical_url")
            ps = part.get("partselect_number", "UNKNOWN")
            if not url:
                part["price_cents"] = None
                part["stock_status"] = "unknown"
                enriched.append(part)
                continue

            ok = False
            last_err = None

            for attempt in range(args.retries + 1):
                try:
                    out = scrape_one(page, part)
                    enriched.append(out)
                    ok = True
                    print(f"\n[{idx}/{len(parts)}] {ps}: ✅ Success\n")
                    break
                except PlaywrightTimeoutError as e:
                    last_err = f"timeout: {e}"
                except Exception as e:
                    last_err = f"error: {e}"

                time.sleep(1.5)

            if not ok:
                part = dict(part)
                part["price_cents"] = None
                part["stock_status"] = "unknown"
                part["scrape_error"] = last_err
                enriched.append(part)
                print(f"\n[{idx}/{len(parts)}] {ps}: ❌ FAILED ({last_err})\n")

            time.sleep(max(0, args.delay_ms) / 1000.0)

        context.close()
        browser.close()

    out_data = {"parts": enriched}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"✅ Wrote: {args.output}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
