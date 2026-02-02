"""Installation instruction extraction using Playwright and OpenAI."""
from __future__ import annotations

import re
from typing import Optional, Dict
from playwright.async_api import async_playwright
import openai
from config import settings


async def extract_install_instructions(url: str, part_name: str, part_number: str) -> Optional[str]:
    """
    Extract installation instructions from a PartSelect product page.
    Uses Playwright to scrape the page and OpenAI to summarize.
    
    Args:
        url: Product page URL
        part_name: Name of the part (e.g., "Refrigerator Door Shelf Bin")
        part_number: PartSelect number (e.g., "PS11752778")
    
    Returns:
        Formatted installation instructions or None if not found
    """
    print(f"\n{'='*70}")
    print(f"🔍 EXTRACTING INSTALLATION INSTRUCTIONS")
    print(f"{'='*70}")
    print(f"URL: {url}")
    print(f"Part: {part_name} ({part_number})\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        try:
            print(f"📡 Loading page...")
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2000)  # Allow JS to render
            print(f"✅ Page loaded\n")
            
            # Extract all relevant content sections
            extracted_data = {}
            
            # 1. Product description
            print(f"🔎 Step 1: Extracting product description...")
            try:
                # Try multiple selectors for product description
                desc_text = None
                
                # Try structured data first
                desc_elem = page.locator('[itemprop="description"]').first
                if await desc_elem.count() > 0:
                    desc_text = await desc_elem.inner_text()
                
                # Try common class names
                if not desc_text:
                    desc_elem = page.locator('.product-description, .description, #description').first
                    if await desc_elem.count() > 0:
                        desc_text = await desc_elem.inner_text()
                
                # Extract from page text as fallback
                if not desc_text:
                    page_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                    # Look for description-like content in first 2000 chars
                    if page_text and len(page_text) > 100:
                        lines = page_text.split('\n')[:30]  # First 30 lines
                        desc_text = '\n'.join([l.strip() for l in lines if len(l.strip()) > 20])[:500]
                
                if desc_text and len(desc_text) > 50:
                    extracted_data["description"] = desc_text
                    print(f"   ✅ Found description ({len(desc_text)} chars)")
                else:
                    print(f"   ❌ No description found")
            except Exception as e:
                print(f"   ❌ Error extracting description: {e}")
            
            # 2. Installation section
            print(f"\n🔎 Step 2: Extracting installation instructions...")
            try:
                # Look for installation-related headers and content
                install_section = await page.evaluate("""
                    () => {
                        const text = document.body.innerText;
                        const lines = text.split('\\n');
                        let capturing = false;
                        let content = [];
                        
                        for (let i = 0; i < lines.length; i++) {
                            const line = lines[i].trim();
                            const lower = line.toLowerCase();
                            
                            // Start capturing at installation section
                            if (lower.includes('installation') || 
                                lower.includes('install instructions') ||
                                lower.includes('how to install') ||
                                lower.includes('replacement instructions')) {
                                capturing = true;
                                content.push(line);
                                continue;
                            }
                            
                            // Stop at next major section
                            if (capturing && (
                                lower.includes('troubleshooting') ||
                                lower.includes('specifications') ||
                                lower.includes('reviews') ||
                                lower.includes('questions') ||
                                lower.includes('related parts')
                            )) {
                                break;
                            }
                            
                            if (capturing && line.length > 10) {
                                content.push(line);
                            }
                            
                            // Limit to 50 lines
                            if (content.length > 50) break;
                        }
                        
                        return content.join('\\n');
                    }
                """)
                
                if install_section and len(install_section) > 50:
                    extracted_data["installation"] = install_section
                    print(f"   ✅ Found installation section ({len(install_section)} chars)")
                else:
                    print(f"   ⚠️  No dedicated installation section found")
            except Exception as e:
                print(f"   ❌ Error extracting installation: {e}")
            
            # 3. Product features/specifications
            print(f"\n🔎 Step 3: Extracting product features...")
            try:
                features_text = None
                
                # Try multiple selectors
                features_elem = page.locator('.features, .specifications, [itemprop="additionalProperty"], .product-details')
                if await features_elem.count() > 0:
                    features_text = await features_elem.first.inner_text()
                
                # Extract "Product Description" section if exists
                if not features_text:
                    page_text = await page.evaluate("""
                        () => {
                            const text = document.body.innerText;
                            const lines = text.split('\\n');
                            let capturing = false;
                            let content = [];
                            
                            for (let i = 0; i < lines.length; i++) {
                                const line = lines[i].trim();
                                const lower = line.toLowerCase();
                                
                                if (lower.includes('product description') || 
                                    lower.includes('product details') ||
                                    lower.includes('part details')) {
                                    capturing = true;
                                    continue;
                                }
                                
                                if (capturing && (
                                    lower.includes('installation') ||
                                    lower.includes('troubleshooting') ||
                                    lower.includes('specifications') ||
                                    lower.includes('reviews')
                                )) {
                                    break;
                                }
                                
                                if (capturing && line.length > 10) {
                                    content.push(line);
                                }
                                
                                if (content.length > 20) break;
                            }
                            
                            return content.join('\\n');
                        }
                    """)
                    if page_text and len(page_text) > 50:
                        features_text = page_text
                
                if features_text and len(features_text) > 20:
                    extracted_data["features"] = features_text[:500]  # Limit length
                    print(f"   ✅ Found features ({len(features_text)} chars)")
                else:
                    print(f"   ❌ No features found")
            except Exception as e:
                print(f"   ❌ Error extracting features: {e}")
            
            # 4. Safety warnings
            print(f"\n🔎 Step 4: Extracting safety warnings...")
            try:
                safety_text = await page.evaluate("""
                    () => {
                        const text = document.body.innerText.toLowerCase();
                        const warnings = [];
                        
                        if (text.includes('unplug') || text.includes('disconnect power')) {
                            warnings.push('Disconnect power before installation');
                        }
                        if (text.includes('turn off water') || text.includes('shut off water')) {
                            warnings.push('Turn off water supply');
                        }
                        if (text.includes('wear gloves') || text.includes('protective')) {
                            warnings.push('Wear protective equipment');
                        }
                        
                        return warnings.join('; ');
                    }
                """)
                if safety_text:
                    extracted_data["safety"] = safety_text
                    print(f"   ✅ Found safety warnings")
            except:
                print(f"   ❌ No safety warnings found")
            
            # 5. Tools required
            print(f"\n🔎 Step 5: Extracting tools required...")
            try:
                tools_text = await page.evaluate("""
                    () => {
                        const text = document.body.innerText.toLowerCase();
                        const tools = [];
                        
                        if (text.includes('screwdriver')) tools.push('screwdriver');
                        if (text.includes('wrench')) tools.push('wrench');
                        if (text.includes('pliers')) tools.push('pliers');
                        if (text.includes('no tools') || text.includes('tool-free')) {
                            return 'No tools required';
                        }
                        
                        return tools.length > 0 ? tools.join(', ') : null;
                    }
                """)
                if tools_text:
                    extracted_data["tools"] = tools_text
                    print(f"   ✅ Tools: {tools_text}")
            except:
                print(f"   ❌ No tools info found")
            
            print(f"\n{'='*70}")
            print(f"📊 EXTRACTION COMPLETE")
            print(f"{'='*70}")
            print(f"Sections extracted: {', '.join(extracted_data.keys())}")
            print(f"{'='*70}\n")
            
            # If we have any content, use OpenAI to summarize
            # Even if limited content, OpenAI can generate useful instructions from part name
            if extracted_data or True:  # Always try OpenAI, even with minimal data
                return await _summarize_with_openai(extracted_data, part_name, part_number)
            else:
                print("❌ No installation content found")
                return None
                
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
            return None
        finally:
            await browser.close()


async def _summarize_with_openai(extracted_data: Dict[str, str], part_name: str, part_number: str) -> Optional[str]:
    """Use OpenAI to create clear installation instructions from extracted content."""
    print(f"🤖 Using OpenAI to generate installation instructions...")
    
    # Build context for OpenAI
    context_parts = []
    
    if "description" in extracted_data and extracted_data["description"]:
        context_parts.append(f"**Product Description:**\n{extracted_data['description'][:500]}")
    
    if "installation" in extracted_data and extracted_data["installation"]:
        context_parts.append(f"**Installation Content:**\n{extracted_data['installation'][:1000]}")
    
    if "features" in extracted_data and extracted_data["features"]:
        context_parts.append(f"**Features:**\n{extracted_data['features'][:300]}")
    
    if "safety" in extracted_data and extracted_data["safety"]:
        context_parts.append(f"**Safety:**\n{extracted_data['safety']}")
    
    if "tools" in extracted_data and extracted_data["tools"]:
        context_parts.append(f"**Tools:**\n{extracted_data['tools']}")
    
    # If no context extracted, at least use part name
    if not context_parts:
        context = f"(No specific content extracted from page. Generate instructions based on part type.)"
    else:
        context = "\n\n".join(context_parts)
    
    # OpenAI prompt
    prompt = f"""You are a helpful assistant providing installation instructions for appliance parts.

Part Information:
- Part Name: {part_name}
- Part Number: {part_number}

Content extracted from PartSelect product page:
{context}

Based on the part information and extracted content above, provide clear, step-by-step installation instructions.

Requirements:
1. Infer the installation process from the part name and type
2. Start with any safety warnings (disconnect power, turn off water, etc.)
   - For simple accessory parts (shelf, bin, drawer, knob), no power disconnection needed
   - For electrical/mechanical parts (motor, pump, heating element), require power disconnection
3. List any tools required (or state "No tools required")
   - Simple parts: usually tool-free, snap-in
   - Complex parts: screwdriver, wrench, pliers as needed
4. Provide 3-5 clear installation steps based on part type:
   - Shelves/bins: Remove old → align tabs → snap in → test
   - Filters: Locate old filter → twist/pull out → insert new → test water
   - Seals: Remove old seal → clean groove → press new seal into channel → check fit
   - Motors/pumps: Disconnect power → remove access panel → disconnect wires → unbolt old → install new → reconnect
5. Keep it concise and actionable
6. Always end with a note about visiting PartSelect for diagrams/videos

Format your response as:
**Safety First:**
[safety steps or "No power disconnection needed for this accessory part"]

**Tools Needed:**
[tools or "No tools required"]

**Installation Steps:**
1. [step]
2. [step]
3. [step]

Keep the response under 250 words and very practical."""

    try:
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cost-effective
            messages=[
                {"role": "system", "content": "You are a helpful assistant providing appliance repair guidance."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more factual responses
            max_tokens=500
        )
        
        instructions = response.choices[0].message.content.strip()
        print(f"✅ Generated instructions ({len(instructions)} chars)")
        return instructions
        
    except Exception as e:
        print(f"❌ OpenAI API failed: {e}")
        return None
