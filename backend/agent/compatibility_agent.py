"""Compatibility sub-agent.

Handles:
- part/model compatibility checks
- cross-brand logic
- dynamic scraping-based compatibility
"""

from typing import Dict, Any, Optional

from models import ChatResponse


async def handle_compatibility(
    orchestrator: "AgentOrchestrator",
    message: str,
    entities: Dict[str, Any],
    context: Dict[str, Any],
    session_id: Optional[str] = None,
) -> ChatResponse:
    """Logic extracted from AgentOrchestrator._handle_compatibility."""
    from database import get_db

    db = get_db()
    part_number = entities.get("part_number")
    model_number = entities.get("model_number") or context.get("modelNumber")

    # CONTEXT FIX: If no part number in current message, look back at history
    if not part_number and session_id:
        print(f"\n🔍 Looking back for part number in conversation history...")
        history = db.table("chat_messages").select("content").eq(
            "session_id", session_id
        ).eq("role", "user").order("created_at", desc=True).limit(10).execute()

        if history.data:
            for item in history.data:
                content = item.get("content", "").strip()
                if not content or len(content) < 5:
                    continue

                # Extract part number from historical message
                historical_entities = orchestrator._extract_entities(content)
                if historical_entities.get("part_number"):
                    part_number = historical_entities["part_number"]
                    print(f"   Found part number in history: {part_number}")
                    break

    # GUARDRAIL: Must have part number
    if not part_number:
        return ChatResponse(
            assistant_text=(
                "To check compatibility, I need the part number. "
                "Please provide the PartSelect number (PS####) or share the product link."
            ),
            cards=[],
            quick_replies=["Example: PS11701542", "Share PartSelect link"],
        )

    # GUARDRAIL: Must have model number
    if not model_number:
        return ChatResponse(
            assistant_text=(
                "To check compatibility, I need your appliance's model number. "
                "You can usually find it on a label inside the door or on the back of the appliance."
            ),
            cards=[
                {
                    "type": "ask_model_number",
                    "id": "ask_model_1",
                    "data": {
                        "reason": "compatibility_check",
                        "help_url": "https://www.partselect.com/FixModelNumber.aspx",
                    },
                }
            ],
            quick_replies=["Where do I find my model number?"],
        )

    # NEW: Check if model number is complete (handle "WDT780..." scenarios)
    normalized_result = await orchestrator._normalize_partial_identifier(model_number, "model")

    if not normalized_result["is_complete"] and normalized_result["suggestions"]:
        # Model number looks incomplete - ask for clarification
        suggestions = normalized_result["suggestions"][:3]
        return ChatResponse(
            assistant_text=(
                f"I found your model prefix **{normalized_result['normalized']}**, but I need the full model number to verify compatibility. "
                f"Did you mean one of these?"
            ),
            cards=[],
            quick_replies=suggestions + ["I'll check my appliance label"],
        )
    elif not normalized_result["is_complete"] and not normalized_result["suggestions"]:
        # Incomplete and no suggestions - ask user to verify
        return ChatResponse(
            assistant_text=(
                f"The model number **{model_number}** looks incomplete. "
                f"Can you check the full model number on your appliance? It's usually 8-12 characters (e.g., WDT780SAEM1)."
            ),
            cards=[],
            quick_replies=["Where's my model number?"],
        )

    # GUARDRAIL: Tool-verified compatibility check (no guessing)
    normalized_model = normalized_result["normalized"] or model_number.upper().replace(" ", "").replace("-", "")

    # NEW: Primary compatibility check - scrape model page to see if part is listed
    print(f"\n🔍 PRIMARY CHECK: Scraping model page to verify part is listed...")
    try:
        from services.model_parts_scraper import check_part_in_model_list
        
        model_list_result = await check_part_in_model_list(part_number, normalized_model)
        
        if model_list_result["is_listed"]:
            # PART IS LISTED ON MODEL PAGE - DEFINITIVE COMPATIBILITY
            print(f"✅ Part {part_number} is listed on model {normalized_model} page!")
            print(f"   Model URL: {model_list_result['model_url']}")
            print(f"   Total parts on model: {model_list_result['total_parts_on_model']}")
            
            # Get part details for response
            part_result = db.table("parts").select("appliance_type, name, brand").eq(
                "partselect_number", part_number
            ).execute()
            
            if part_result.data:
                part = part_result.data[0]
                return ChatResponse(
                    version="1.1",
                    intent="compatibility_check",
                    source="scraper+llm",
                    assistant_text=(
                        f"✅ **Compatible**: Part {part_number} ({part['name']}) is confirmed compatible with model {normalized_model}.\n\n"
                        f"This part is listed on the model's parts page, confirming compatibility."
                    ),
                    cards=[
                        {
                            "type": "compatibility",
                            "id": "compat_model_page",
                            "data": {
                                "status": "fits",
                                "partselect_number": part_number,
                                "model_number": normalized_model,
                                "reason": f"This part is listed on the model {normalized_model} parts page, confirming compatibility.",
                                "confidence": "exact",
                                "evidence": {
                                    "url": model_list_result["model_url"],
                                    "snippet": f"Found on model page with {model_list_result['total_parts_on_model']} total parts"
                                },
                                "modelPageUrl": model_list_result["model_url"]
                            },
                        }
                    ],
                    quick_replies=["Add to cart", "Installation help", "View all parts for this model"],
                )
        else:
            print(f"❌ Part {part_number} NOT found on model {normalized_model} page")
            print(f"   Model URL: {model_list_result['model_url']}")
            print(f"   Total parts checked: {model_list_result['total_parts_on_model']}")
            
            # Part not found on model page - likely not compatible
            part_result = db.table("parts").select("appliance_type, name, brand").eq(
                "partselect_number", part_number
            ).execute()
            
            if part_result.data:
                part = part_result.data[0]
                return ChatResponse(
                    version="1.1",
                    intent="compatibility_check",
                    source="scraper+llm",
                    assistant_text=(
                        f"❌ **Not Compatible**: Part {part_number} ({part['name']}) does not appear to be compatible with model {normalized_model}.\n\n"
                        f"This part is not listed on the model's parts page. Please verify the part number or model number."
                    ),
                    cards=[
                        {
                            "type": "compatibility",
                            "id": "compat_not_on_model",
                            "data": {
                                "status": "no_fit",
                                "partselect_number": part_number,
                                "model_number": normalized_model,
                                "reason": f"This part is not listed on the model {normalized_model} parts page.",
                                "confidence": "high",
                                "evidence": {
                                    "url": model_list_result["model_url"],
                                    "snippet": f"Checked {model_list_result['total_parts_on_model']} parts on model page"
                                },
                                "modelPageUrl": model_list_result["model_url"]
                            },
                        }
                    ],
                    quick_replies=["Search for compatible parts", "Verify model number", "View all parts for this model"],
                )
    except Exception as e:
        print(f"⚠️  Model page scraping failed: {e}")
        print(f"   Falling back to other compatibility checks...")
        # Continue with existing fallback methods

    # Check if part exists first
    part_result = db.table("parts").select("appliance_type, name, brand").eq(
        "partselect_number", part_number
    ).execute()

    if not part_result.data:
        return ChatResponse(
            assistant_text=(
                f"I don't have part {part_number} in my catalog. "
                "Please verify the part number or share the PartSelect product link."
            ),
            cards=[],
            quick_replies=["Search for parts"],
        )

    part = part_result.data[0]

    # QUICK GUARDRAIL: obvious appliance mismatch (e.g. refrigerator part vs dishwasher model)
    part_appliance = part.get("appliance_type")

    # Try to infer appliance from entities/context or model pattern
    inferred_model_appliance: Optional[str] = entities.get("appliance_type") or context.get(
        "appliance"
    )
    if not inferred_model_appliance and model_number:
        model_upper = model_number.upper()
        # Very small heuristic set for Whirlpool/KitchenAid dishwashers vs refrigerators
        if model_upper.startswith(("WDT", "KDT", "MDB", "GU", "DU")):
            inferred_model_appliance = "dishwasher"
        elif model_upper.startswith(("WRF", "WRS", "MFI", "EDR", "KRFF", "GX", "GS")):
            inferred_model_appliance = "refrigerator"

    if part_appliance and inferred_model_appliance and part_appliance != inferred_model_appliance:
        # We can safely say this doesn't fit: wrong category
        return ChatResponse(
            assistant_text=(
                f"❌ **Not Compatible**: Part {part_number} ({part['name']}) is a "
                f"{part_appliance} part, but your model {model_number} is a {inferred_model_appliance}. "
                f"This part is not designed for that appliance type."
            ),
            cards=[
                {
                    "type": "compatibility",
                    "id": "compat_appliance_mismatch",
                    "data": {
                        "status": "does_not_fit",
                        "partselect_number": part_number,
                        "model_number": model_number,
                        "reason": (
                            f"Appliance type mismatch: part={part_appliance}, model={inferred_model_appliance}"
                        ),
                        "confidence": "high",
                    },
                }
            ],
            quick_replies=["Search other parts"],
        )

    # Check compatibility in database first
    result = db.table("model_parts").select("*").eq(
        "partselect_number", part_number
    ).eq("model_number", normalized_model).execute()

    if result.data and result.data[0].get("confidence") == "exact":
        # VERIFIED COMPATIBILITY (from database)
        record = result.data[0]
        model_page_url = f"https://www.partselect.com/Models/{normalized_model}"
        return ChatResponse(
            version="1.1",
            intent="compatibility_check",
            source="db",
            assistant_text=(
                f"✅ **Verified**: Part {part_number} ({part['name']}) is confirmed compatible with model {model_number}."
            ),
            cards=[
                {
                    "type": "compatibility",
                    "id": "compat_1",
                    "data": {
                        "status": "fits",
                        "partselect_number": part_number,
                        "model_number": model_number,
                        "reason": f"This part is confirmed compatible with model {model_number}.",
                        "confidence": "exact",
                        "evidence": {
                            "url": record.get("evidence_url"),
                            "snippet": record.get("evidence_snippet"),
                        },
                        "modelPageUrl": model_page_url,
                    },
                }
            ],
            quick_replies=["Add to cart", "Installation help", "View all parts for this model"],
        )

    # Database didn't have info - try cross-brand compatibility first (NEW!)
    print(f"\n🔧 Database has no compatibility data. Checking cross-brand compatibility...")

    # Get full part details
    full_part_result = db.table("parts").select("*").eq(
        "partselect_number", part_number
    ).execute()

    compat_result: Optional[Dict[str, Any]] = None
    product_url: Optional[str] = None

    if full_part_result.data:
        part_full = full_part_result.data[0]
        part_brand = part_full.get("brand", "")
        detected_brand = entities.get("brand")  # User-mentioned brand

        if part_brand and detected_brand:
            print(f"   Part brand: {part_brand}, Model brand: {detected_brand}")
            from services.cross_brand import check_cross_brand_compatibility

            cross_brand_result = await check_cross_brand_compatibility(
                part_brand=part_brand,
                model_number=model_number,
                detected_brand=detected_brand,
            )

            if cross_brand_result["is_compatible"] is True:
                # Cross-brand match found!
                return ChatResponse(
                    assistant_text=(
                        f"✅ **Cross-Brand Match**: {cross_brand_result['reason']}\n\n"
                        f"*Confidence: {int(cross_brand_result['confidence'] * 100)}%*"
                    ),
                    cards=[
                        {
                            "type": "compatibility",
                            "id": "compat_cross_brand",
                            "data": {
                                "status": "fits",
                                "partselect_number": part_number,
                                "model_number": model_number,
                                "reason": cross_brand_result["reason"],
                                "confidence": "high",
                            },
                        }
                    ],
                    quick_replies=["Add to cart", "Installation help", "View on PartSelect"],
                )
            elif cross_brand_result["is_compatible"] is False:
                # Definitely not compatible due to cross-brand rules
                return ChatResponse(
                    assistant_text=(
                        f"❌ **Not Compatible**: {cross_brand_result['reason']}\n\n"
                        f"*Confidence: {int(cross_brand_result['confidence'] * 100)}%*"
                    ),
                    cards=[
                        {
                            "type": "compatibility",
                            "id": "compat_not_cross_brand",
                            "data": {
                                "status": "does_not_fit",
                                "partselect_number": part_number,
                                "model_number": model_number,
                                "reason": cross_brand_result["reason"],
                                "confidence": "high",
                            },
                        }
                    ],
                    quick_replies=["Search for compatible parts"],
                )
            else:
                print(f"   ⚠️  Cross-brand check inconclusive: {cross_brand_result['reason']}")

        # Cross-brand didn't help - try dynamic scraping
        print(f"\n🔧 Attempting dynamic scraping...")

        part_full = full_part_result.data[0]
        product_url = part_full.get("canonical_url") or part_full.get("product_url")
        manufacturer_part = part_full.get("manufacturer_number") or ""

        if product_url:
            try:
                from services.compatibility_scraper import check_part_compatibility

                compat_result = await check_part_compatibility(
                    product_url=product_url,
                    part_number=part_number,
                    manufacturer_part=manufacturer_part,
                    user_model=model_number,
                )

                # If scraping succeeded and got a result
                if compat_result.get("compatible") is not None:
                    is_compatible = compat_result["compatible"]
                    confidence = compat_result.get("confidence", "unknown")
                    reason = compat_result.get("reason", "")

                    if is_compatible:
                        # COMPATIBLE
                        return ChatResponse(
                            assistant_text=(
                                f"✅ **Compatible**: Part {part_number} ({part['name']}) appears to be compatible with model {model_number}.\n\n"
                                f"**Reason:** {reason}\n\n"
                                f"*Confidence: {confidence.capitalize()}*"
                            ),
                            cards=[
                                {
                                    "type": "compatibility",
                                    "id": "compat_scraped",
                                    "data": {
                                        "status": "fits",
                                        "partselect_number": part_number,
                                        "model_number": model_number,
                                        "reason": reason,
                                        "confidence": confidence,
                                    },
                                }
                            ],
                            quick_replies=["Add to cart", "Installation help", "Verify on PartSelect"],
                        )
                    else:
                        # NOT COMPATIBLE
                        return ChatResponse(
                            assistant_text=(
                                f"❌ **Not Compatible**: Part {part_number} ({part['name']}) does not appear to be compatible with model {model_number}.\n\n"
                                f"**Reason:** {reason}\n\n"
                                f"*Confidence: {confidence.capitalize()}*"
                            ),
                            cards=[
                                {
                                    "type": "compatibility",
                                    "id": "compat_not_fit",
                                    "data": {
                                        "status": "does_not_fit",
                                        "partselect_number": part_number,
                                        "model_number": model_number,
                                        "reason": reason,
                                        "confidence": confidence,
                                    },
                                }
                            ],
                            quick_replies=["Search for compatible parts", "Verify on PartSelect"],
                        )

            except Exception as e:  # pragma: no cover - scraping issues
                print(f"⚠️  Compatibility scraping failed: {e}")
                compat_result = None

    # If scraping found replacement parts but couldn't determine compatibility
    if compat_result and compat_result.get("replaces") and compat_result.get("compatible") is None:
        replaces_list = compat_result["replaces"][:10]  # Show first 10
        works_with = compat_result.get("works_with")
        part_url = product_url or f"https://www.partselect.com/Search.aspx?SearchTerm={part_number}"

        # Build enriched explanation using scraped UI context
        extra_context_lines = []
        if works_with:
            extra_context_lines.append(
                f"This part is designed for **{works_with}s** based on PartSelect's product page."
            )
        if replaces_list:
            extra_context_lines.append(
                "This part replaces these manufacturer part numbers:\n"
                f"{', '.join(replaces_list)}"
            )

        extra_context_text = "\n\n".join(extra_context_lines)

        return ChatResponse(
            assistant_text=(
                f"⚠️ I cannot definitively verify compatibility for part {part_number} with model {model_number} based on available data.\n\n"
                f"{extra_context_text}\n\n"
                f"If your appliance uses any of the replacement numbers above, this part is very likely compatible. "
                f"Otherwise, please verify on PartSelect using their model lookup tool."
            ),
            cards=[
                {
                    "type": "compatibility",
                    "id": "compat_uncertain",
                    "data": {
                        "status": "need_info",
                        "partselect_number": part_number,
                        "model_number": model_number,
                        "reason": (
                            f"This part works with: {works_with or 'Unknown'}; "
                            f"replaces: {', '.join(replaces_list[:5])}..."
                        ),
                        "verifyUrl": part_url,
                    },
                }
            ],
            quick_replies=["Verify on PartSelect", "Search other parts"],
        )

    # Fallback: CANNOT VERIFY (no data at all)
    part_url = f"https://www.partselect.com/Search.aspx?SearchTerm={part_number}"
    return ChatResponse(
        assistant_text=(
            f"⚠️ I cannot verify compatibility for part {part_number} with model {model_number}. "
            f"Please verify directly on PartSelect using their model lookup tool to ensure this part fits your specific appliance."
        ),
        cards=[
            {
                "type": "compatibility",
                "id": "compat_1",
                "data": {
                    "status": "need_info",
                    "partselect_number": part_number,
                    "model_number": model_number,
                    "reason": "Compatibility data not available in our database. Manual verification required.",
                    "verifyUrl": part_url,
                },
            }
        ],
        quick_replies=["Verify on PartSelect", "Search other parts"],
    )

