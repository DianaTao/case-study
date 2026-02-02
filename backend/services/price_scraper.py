"""Price and availability extraction using Playwright."""
from __future__ import annotations

import json
import re
from typing import Optional, Tuple

from playwright.async_api import async_playwright


def _to_cents(price_str: Optional[str]) -> Optional[int]:
    if not price_str:
        return None
    match = re.search(r"(\d+(?:\.\d{1,2})?)", price_str.replace(",", ""))
    if not match:
        return None
    value = float(match.group(1))
    return int(round(value * 100))


def _normalize_availability(raw: Optional[str]) -> str:
    if not raw:
        return "unknown"
    lowered = raw.lower()
    if "instock" in lowered or "in stock" in lowered:
        return "in_stock"
    if "outofstock" in lowered or "out of stock" in lowered:
        return "out_of_stock"
    if "backorder" in lowered or "back order" in lowered:
        return "backorder"
    return "unknown"


async def fetch_price_and_stock(url: str) -> Tuple[Optional[int], str]:
    """Fetch price/stock from a product URL using JSON-LD + DOM fallback."""
    print(f"\n{'='*70}")
    print(f"🔍 STARTING PRICE EXTRACTION")
    print(f"{'='*70}")
    print(f"URL: {url}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            print(f"📡 Loading page...")
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(1500)
            print(f"✅ Page loaded\n")

            print(f"🔎 Step 1: Checking JSON-LD scripts...")
            jsonld_blocks = await page.eval_on_selector_all(
                'script[type="application/ld+json"]',
                "nodes => nodes.map(n => n.textContent).filter(Boolean)"
            )
            print(f"   Found {len(jsonld_blocks)} JSON-LD blocks")

            price_cents = None
            availability = "unknown"

            for idx, raw in enumerate(jsonld_blocks):
                try:
                    parsed = json.loads(raw)
                    print(f"   Block {idx+1}: {str(parsed)[:200]}...")
                except Exception as e:
                    print(f"   Block {idx+1}: Parse error - {e}")
                    continue

                candidates = []
                if isinstance(parsed, list):
                    candidates = parsed
                elif isinstance(parsed, dict) and parsed.get("@graph"):
                    candidates = parsed.get("@graph", [])
                else:
                    candidates = [parsed]

                for candidate in candidates:
                    if not isinstance(candidate, dict):
                        continue
                    candidate_type = str(candidate.get("@type", "")).lower()
                    if candidate_type not in ("product", "") and not candidate.get("offers"):
                        continue
                    offers = candidate.get("offers")
                    if isinstance(offers, list) and offers:
                        offers = offers[0]
                    if isinstance(offers, dict):
                        price_cents = price_cents or _to_cents(str(offers.get("price", "")))
                        availability = _normalize_availability(str(offers.get("availability", "")))
                        if price_cents or availability != "unknown":
                            print(f"   ✅ Found in JSON-LD: price={price_cents}, availability={availability}")

                if price_cents is not None or availability != "unknown":
                    break
            
            if price_cents is None and availability == "unknown":
                print(f"   ❌ No data in JSON-LD\n")
            else:
                print()

            if price_cents is None or availability == "unknown":
                print(f"🔎 Step 2: Checking meta tags...")
                meta = await page.eval_on_selector_all(
                    "meta",
                    """nodes => nodes.map(n => ({
                        name: n.getAttribute('name'),
                        property: n.getAttribute('property'),
                        content: n.getAttribute('content')
                    }))"""
                )
                print(f"   Found {len(meta)} meta tags")
                for entry in meta:
                    key = (entry.get("property") or entry.get("name") or "").lower()
                    value = entry.get("content") or ""
                    if price_cents is None and key in {
                        "product:price:amount",
                        "og:price:amount",
                        "price",
                        "product:price",
                        "og:price",
                    }:
                        price_cents = _to_cents(value)
                        if price_cents:
                            print(f"   ✅ Found price in meta[{key}]: {value}")
                    if availability == "unknown" and key in {
                        "product:availability",
                        "availability",
                        "product:stock_status",
                    }:
                        availability = _normalize_availability(value)
                        if availability != "unknown":
                            print(f"   ✅ Found availability in meta[{key}]: {value}")
                
                if price_cents is None and availability == "unknown":
                    print(f"   ❌ No data in meta tags\n")
                else:
                    print()

            if price_cents is None or availability == "unknown":
                print(f"🔎 Step 3: Checking DOM selectors...")
                selector_candidates = [
                    '[itemprop="price"]',
                    '[data-testid*="price"]',
                    ".price",
                    ".product-price",
                    ".price-value",
                    ".price .value",
                ]
                for selector in selector_candidates:
                    if price_cents is None:
                        locator = page.locator(selector).first
                        count = await locator.count()
                        if count:
                            text = (await locator.inner_text()).strip()
                            print(f"   Found selector '{selector}': {text}")
                            price_cents = _to_cents(text)
                            if price_cents:
                                print(f"   ✅ Extracted price: {price_cents} cents")
                                break
                
                if price_cents is None:
                    print(f"   ❌ No price in DOM selectors\n")
                else:
                    print()

            if price_cents is None or availability == "unknown":
                print(f"🔎 Step 4: Checking body text (last resort)...")
                raw_body = await page.inner_text("body")
                body_text_lower = raw_body.lower()

                if price_cents is None:
                    # Strategy 1: Look for explicit $xx.xx
                    match = re.search(r"\$\s*\d+(?:\.\d{2})?", raw_body)
                    if match:
                        print(f"   Found price pattern with $ in body: {match.group(0)}")
                        price_cents = _to_cents(match.group(0))
                    else:
                        # Strategy 2: Look for 'price' followed by a number
                        # e.g. "Price: 44.95" or "Our Price 44.95"
                        price_match = re.search(
                            r"(price[:\s]*)(\d+(?:\.\d{2})?)", body_text_lower
                        )
                        if price_match:
                            value_str = price_match.group(2)
                            print(f"   Found 'price' label with value: {value_str}")
                            price_cents = _to_cents(value_str)

                if availability == "unknown":
                    availability = _normalize_availability(body_text_lower)
                    if availability != "unknown":
                        print(f"   Found availability in body: {availability}")
                print()

            print(f"{'='*70}")
            print(f"📊 FINAL RESULT:")
            if price_cents:
                print(f"   💰 Price: ${price_cents/100:.2f} ({price_cents} cents)")
            else:
                print(f"   ❌ Price: NOT FOUND")
            print(f"   📦 Stock: {availability}")
            print(f"{'='*70}\n")

            return price_cents, availability
        finally:
            await browser.close()
