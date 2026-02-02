"""Troubleshooting sub-agent.

Encapsulates all troubleshooting-related logic that used to live in
`AgentOrchestrator`:
- symptom-based part search
- LLM-guided troubleshooting
- branching troubleshooting flows
"""

from typing import Dict, Any, Optional, List
import re

from models import ChatResponse


async def _search_parts_by_symptom(
    symptom: str,
    appliance_type: Optional[str] = None,
) -> List[Dict]:
    """
    Search for parts that fix a given symptom using the symptom-part index.
    Returns list of parts that match the symptom.
    Falls back to empty list if table doesn't exist (migration not run yet).
    """
    from database import get_db

    db = get_db()
    normalized_symptom = symptom.lower().strip()

    print(f"\n🔍 Searching parts by symptom: '{symptom}'")

    try:
        # Search in part_symptoms table with fuzzy matching
        symptom_result = db.table("part_symptoms").select(
            "partselect_number, symptom"
        ).ilike("symptom", f"%{normalized_symptom}%").execute()

        if not symptom_result.data:
            print(f"   ❌ No parts found for symptom: {symptom}")
            return []

        # Get unique part numbers
        part_numbers = list(set([row["partselect_number"] for row in symptom_result.data]))

        # Fetch full part details
        query = db.table("parts").select("*").in_(
            "partselect_number", part_numbers
        )

        # Filter by appliance type if provided
        if appliance_type:
            query = query.eq("appliance_type", appliance_type)

        parts_result = query.execute()
        parts = parts_result.data if parts_result.data else []

        print(f"   ✅ Found {len(parts)} parts matching symptom")
        return parts

    except Exception as e:
        # Table doesn't exist or query failed - gracefully fall back
        print(f"   ⚠️  Symptom search unavailable (table not created): {str(e)}")
        print(f"   💡 Run migration 003_troubleshooting_symptoms.sql to enable symptom search")
        return []


async def _get_symptom_guidance_with_llm(
    orchestrator: "AgentOrchestrator",
    message: str,
    appliance_type: str,
    detected_symptoms: List[str],
) -> Optional[ChatResponse]:
    """
    Use OpenAI + database symptoms to provide troubleshooting guidance and recommend parts.
    """
    from database import get_db
    import openai
    from config import settings

    print(f"\n🤖 Getting symptom guidance with LLM...")

    db = get_db()

    # Query database for parts that fix these symptoms
    relevant_parts: List[Dict[str, Any]] = []
    if detected_symptoms:
        try:
            # Query part_symptoms table for matching symptoms
            for symptom in detected_symptoms[:3]:  # Limit to top 3 symptoms
                result = db.table("part_symptoms").select(
                    "*, parts(*)"
                ).ilike("symptom", f"%{symptom}%").eq(
                    "parts.appliance_type", appliance_type
                ).limit(5).execute()

                if result.data:
                    for item in result.data:
                        if item.get("parts"):
                            relevant_parts.append(item["parts"])
        except Exception as e:
            print(f"   ⚠️  Database symptom query failed: {e}")

    # If no symptom matches, get common parts for the appliance
    if not relevant_parts:
        result = db.table("parts").select("*").eq(
            "appliance_type", appliance_type
        ).limit(10).execute()
        if result.data:
            relevant_parts = result.data

    if not relevant_parts:
        return None

    # Build context for OpenAI
    parts_context: List[str] = []
    for part in relevant_parts[:5]:  # Top 5 parts
        symptoms = part.get("troubleshooting_symptoms") or []
        parts_context.append(
            f"- {part['name']} (PS{part['partselect_number']}): "
            f"Fixes symptoms like {', '.join(symptoms[:3]) if symptoms else 'general issues'}"
        )

    parts_info = "\n".join(parts_context)

    # OpenAI prompt for troubleshooting guidance
    prompt = f"""You are a helpful appliance repair assistant.

User's Issue: "{message}"
Appliance Type: {appliance_type}
Detected Symptoms: {', '.join(detected_symptoms) if detected_symptoms else 'general issue'}

Relevant Parts from Database:
{parts_info}

Task:
1. Provide 2-3 diagnostic steps the user can check themselves
2. Recommend 1-2 specific parts that are most likely to fix the issue
3. Explain WHY those parts would help
4. Keep it concise (under 200 words)

Format your response as:
**Diagnostic Steps:**
1. [Check something]
2. [Check something else]

**Likely Cause & Solution:**
[Brief explanation]

**Recommended Parts:**
- [Part Name] (PS####): [Why this helps]

Keep it practical and specific to the user's issue."""

    try:
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful appliance repair assistant. Provide practical troubleshooting advice.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        guidance_text = response.choices[0].message.content.strip()

        # Post-process common formatting glitches from LLM (e.g., "PSPS11701542")
        guidance_text = re.sub(r"\bPSPS(\d{6,9})\b", r"PS\1", guidance_text)
        print(f"✅ Generated troubleshooting guidance")

        # Extract PS numbers mentioned in the response
        recommended_ps_numbers = re.findall(r"PS(\d{6,9})", guidance_text)

        # Create product cards for recommended parts
        cards: List[Dict[str, Any]] = []
        for ps_num in recommended_ps_numbers[:2]:  # Max 2 cards
            ps_full = f"PS{ps_num}"
            part_result = db.table("parts").select("*").eq(
                "partselect_number", ps_full
            ).execute()

            if part_result.data:
                part = part_result.data[0]

                # If price is missing, try to fetch it dynamically
                if part.get("price_cents") is None or part.get("stock_status") == "unknown":
                    product_url = part.get("canonical_url") or part.get("product_url")
                    if product_url:
                        try:
                            print(f"💰 Fetching price for {ps_full}...")
                            from services.price_scraper import fetch_price_and_stock
                            from datetime import datetime

                            price_cents, availability = await fetch_price_and_stock(product_url)

                            if price_cents is not None:
                                # Update part data with fetched price
                                part["price_cents"] = price_cents
                                part["stock_status"] = availability
                                part["updated_at"] = datetime.utcnow().isoformat() + "Z"
                                print(f"✅ Fetched price: ${price_cents / 100:.2f}, stock: {availability}")

                                # Update database
                                db.table("parts").update(
                                    {
                                        "price_cents": price_cents,
                                        "stock_status": availability,
                                    }
                                ).eq("partselect_number", ps_full).execute()
                            else:
                                print(f"⚠️  No price found")
                        except Exception as e:  # pragma: no cover - network / scraping
                            print(f"⚠️  Price fetch failed: {e}")

                card = orchestrator._create_product_card(part)
                cards.append(card)

        return ChatResponse(
            assistant_text=guidance_text,
            cards=cards,
            quick_replies=["Check compatibility", "Installation help", "Other issues"],
        )

    except Exception as e:  # pragma: no cover - external LLM errors
        print(f"❌ LLM symptom guidance failed: {e}")
        return None


async def handle_troubleshoot(
    orchestrator: "AgentOrchestrator",
    message: str,
    entities: Dict[str, Any],
    context: Dict[str, Any],
) -> ChatResponse:
    """
    Handle troubleshooting requests with branching decision tree.
    GUARDRAIL: Symptom-first (not part-first) diagnostic flow.
    GUARDRAIL: Hard filter by appliance_type to prevent category leakage.
    GUARDRAIL: Ask for model number early to drive toward verified recommendations.
    """
    from database import get_db

    # GUARDRAIL: Must have appliance type (from entities or context)
    appliance_type = entities.get("appliance_type") or context.get("appliance")

    if not appliance_type:
        return ChatResponse(
            assistant_text="What type of appliance are you troubleshooting? Please mention if it's a refrigerator or dishwasher.",
            cards=[],
            quick_replies=["Refrigerator", "Dishwasher"],
        )

    lower_msg = message.lower()
    detected_symptoms = entities.get("symptoms", [])

    print(f"\n🔧 Troubleshooting for: {appliance_type}")
    print(f"   Symptoms: {detected_symptoms}")

    # CONTEXT FIX: If user just selected appliance without symptoms, ask for them
    if not detected_symptoms and lower_msg.strip() in ["refrigerator", "dishwasher", "fridge"]:
        # User just selected appliance type - ask what's wrong
        if appliance_type == "refrigerator":
            return ChatResponse(
                assistant_text="What issue are you experiencing with your refrigerator?",
                cards=[],
                quick_replies=[
                    "Ice maker not working",
                    "Not cooling properly",
                    "Water dispenser issue",
                    "Leaking water",
                    "Other issue",
                ],
            )
        else:  # dishwasher
            return ChatResponse(
                assistant_text="What issue are you experiencing with your dishwasher?",
                cards=[],
                quick_replies=[
                    "Not cleaning dishes",
                    "Not draining",
                    "Not drying",
                    "Leaking",
                    "Other issue",
                ],
            )

    # Try intelligent symptom-based part recommendations using OpenAI + scraped data
    try:
        symptom_guidance = await _get_symptom_guidance_with_llm(
            orchestrator=orchestrator,
            message=message,
            appliance_type=appliance_type,
            detected_symptoms=detected_symptoms,
        )

        if symptom_guidance:
            return symptom_guidance
    except Exception as e:
        print(f"⚠️  Symptom guidance LLM failed: {e}")

    # Fallback: Detect specific symptoms and route to appropriate flows
    symptom_map: Dict[str, Dict[str, Any]] = {
        "ice maker": {
            "keywords": ["ice maker", "icemaker", "ice machine", "ice dispenser"],
            "flow": "ice_maker_flow",
            "initial_question": "Is the ice maker receiving water?",
            "parts": ["PS11701542", "PS11752778"],  # Water filter, ice maker assembly
        },
        "water dispenser": {
            "keywords": ["water dispenser", "water not dispensing", "no water"],
            "flow": "water_flow",
            "initial_question": "Is the water line connected and valve open?",
            "parts": ["PS11701542"],  # Water filter
        },
        "not cooling": {
            "keywords": ["not cooling", "warm", "not cold", "temperature"],
            "flow": "cooling_flow",
            "initial_question": "Is the compressor running (humming sound)?",
            "parts": ["PS12364199"],  # Common cooling-related parts
        },
        "dishwasher not cleaning": {
            "keywords": ["not cleaning", "dishes dirty", "not washing"],
            "flow": "cleaning_flow",
            "initial_question": "Is water spraying from both spray arms?",
            "parts": ["PS429868"],  # Spray arm, pump
        },
        "dishwasher not draining": {
            "keywords": ["not draining", "water in bottom", "standing water"],
            "flow": "drain_flow",
            "initial_question": "Can you hear the drain pump running?",
            "parts": ["PS429868"],  # Drain pump
        },
    }

    # SYMPTOM-FIRST FLOW: Database symptom search with hard filtering
    if detected_symptoms:
        print(f"\n🔍 Using database symptom search for: {detected_symptoms}")
        print(f"   Hard filter: appliance_type = {appliance_type}")

        all_matching_parts: List[Dict[str, Any]] = []
        for symptom in detected_symptoms:
            # GUARDRAIL: Hard filter by appliance_type to prevent category leakage
            parts = await _search_parts_by_symptom(symptom, appliance_type)
            all_matching_parts.extend(parts)

        # De-duplicate parts
        seen = set()
        unique_parts: List[Dict[str, Any]] = []
        for part in all_matching_parts:
            ps_num = part["partselect_number"]
            # GUARDRAIL: Double-check appliance type (defense in depth)
            if part.get("appliance_type") != appliance_type:
                print(f"   ⚠️  Filtered out {ps_num} - wrong appliance type: {part.get('appliance_type')}")
                continue
            if ps_num not in seen:
                seen.add(ps_num)
                unique_parts.append(part)

        if unique_parts:
            # Found parts via symptom match
            # GUARDRAIL: Ask for model number to verify compatibility before purchase
            model_number = entities.get("model_number") or context.get("modelNumber")

            cards = [orchestrator._create_product_card(part) for part in unique_parts[:5]]
            symptom_text = ", ".join(detected_symptoms)

            if not model_number:
                return ChatResponse(
                    assistant_text=(
                        f"Based on the symptom '{symptom_text}', here are parts that commonly fix this issue. "
                        f"**To verify fit**, please share your appliance's model number (found on a label inside the door or on the back)."
                    ),
                    cards=cards,
                    quick_replies=["Share model number", "Where to find model number"],
                )
            else:
                return ChatResponse(
                    assistant_text=(
                        f"Based on the symptom '{symptom_text}', here are parts that commonly fix this issue for {appliance_type}s. "
                        f"I'll verify compatibility with your model {model_number}."
                    ),
                    cards=cards,
                    quick_replies=[f"Check fit for {model_number}", "Troubleshoot step-by-step"],
                )

    # Fallback: Match symptom to predefined flow
    detected_symptom: Optional[Dict[str, Any]] = None
    for symptom, config in symptom_map.items():
        if any(kw in lower_msg for kw in config["keywords"]):
            detected_symptom = config
            break

    # If no specific symptom, use generic flow
    if not detected_symptom:
        return ChatResponse(
            assistant_text="Let me help you troubleshoot. I'll ask a few questions to narrow down the problem.",
            cards=[
                {
                    "type": "troubleshoot_step",
                    "id": "trouble_generic_1",
                    "data": {
                        "stepNumber": 1,
                        "totalSteps": 3,
                        "question": "Is the appliance receiving power?",
                        "options": [
                            {"label": "Yes", "value": "yes"},
                            {"label": "No", "value": "no"},
                        ],
                        "flowId": "generic_power",
                        "symptom": "generic",
                    },
                }
            ],
            quick_replies=["Need a part"],
        )

    # Return symptom-specific first question
    print(f"\n🔍 Detected symptom flow: {detected_symptom.get('flow')}")
    print(f"   Initial question: {detected_symptom.get('initial_question')}\n")

    return ChatResponse(
        assistant_text="Let me help you troubleshoot. I'll ask a few targeted questions.",
        cards=[
            {
                "type": "troubleshoot_step",
                "id": f"trouble_{detected_symptom['flow']}_1",
                "data": {
                    "stepNumber": 1,
                    "totalSteps": 3,
                    "question": detected_symptom["initial_question"],
                    "options": [
                        {"label": "Yes", "value": "yes"},
                        {"label": "No", "value": "no"},
                    ],
                    "flowId": detected_symptom["flow"],
                    "symptom": detected_symptom["flow"],
                    "recommendedParts": detected_symptom.get("parts", []),
                },
            }
        ],
        quick_replies=["Skip to parts"],
    )


async def handle_troubleshoot_answer(
    orchestrator: "AgentOrchestrator",
    flow_id: str,
    answer: str,
    step: int,
    context: Dict[str, Any],
) -> ChatResponse:
    """
    Handle answers to troubleshooting questions with branching logic.
    Different flows lead to different outcomes and part recommendations.
    """
    from database import get_db

    print(f"\n🔧 Troubleshoot answer received:")
    print(f"   Flow: {flow_id}, Step: {step}, Answer: {answer}\n")

    db = get_db()

    # Ice maker troubleshooting flow
    if "ice_maker" in flow_id:
        if step == 1:
            if answer.lower() == "no":
                return ChatResponse(
                    assistant_text="The water supply is likely the issue. Let's check further.",
                    cards=[
                        {
                            "type": "troubleshoot_step",
                            "id": f"trouble_{flow_id}_2",
                            "data": {
                                "stepNumber": 2,
                                "totalSteps": 3,
                                "question": "Is the water filter more than 6 months old?",
                                "options": [
                                    {"label": "Yes", "value": "yes"},
                                    {"label": "No", "value": "no"},
                                    {"label": "Don't know", "value": "unknown"},
                                ],
                                "flowId": flow_id,
                                "symptom": "ice_maker",
                            },
                        }
                    ],
                )
            else:  # yes - water is reaching
                return ChatResponse(
                    assistant_text="Since water is available, the ice maker assembly itself may be faulty.",
                    cards=[
                        {
                            "type": "troubleshoot_step",
                            "id": f"trouble_{flow_id}_2",
                            "data": {
                                "stepNumber": 2,
                                "totalSteps": 3,
                                "question": "Is the ice maker making any noise at all?",
                                "options": [
                                    {"label": "Yes", "value": "yes"},
                                    {"label": "No", "value": "no"},
                                ],
                                "flowId": flow_id,
                                "symptom": "ice_maker",
                            },
                        }
                    ],
                )

        elif step == 2:
            # GUARDRAIL: Ask for model number before recommending parts
            model_number = context.get("modelNumber")
            appliance_type = context.get("appliance", "refrigerator")

            # Branch: clogged filter vs faulty ice maker
            if answer.lower() == "yes":  # Old filter or making noise
                # Recommend water filter
                part_result = db.table("parts").select("*").eq(
                    "partselect_number", "PS11701542"
                ).eq("appliance_type", appliance_type).execute()  # GUARDRAIL: Hard filter

                if part_result.data:
                    part = part_result.data[0]
                    if not model_number:
                        return ChatResponse(
                            assistant_text=(
                                "Based on your answers, the water filter is likely clogged. "
                                "**To verify fit**, please share your refrigerator's model number (found on a label inside the door)."
                            ),
                            cards=[orchestrator._create_product_card(part)],
                            quick_replies=["Share model number", "Where to find model number"],
                        )
                    else:
                        return ChatResponse(
                            assistant_text=(
                                "Based on your answers, the water filter is likely clogged. "
                                f"Here's a replacement (I'll verify fit for {model_number}):"
                            ),
                            cards=[orchestrator._create_product_card(part)],
                            quick_replies=[f"Check fit for {model_number}", "Add to cart"],
                        )
            else:  # Silent ice maker = mechanical failure
                # Search for ice maker assembly - GUARDRAIL: Hard filter by appliance_type
                search_result = db.table("parts").select("*").ilike(
                    "name", "%ice maker%"
                ).eq("appliance_type", appliance_type).limit(3).execute()

                if search_result.data:
                    cards = [orchestrator._create_product_card(p) for p in search_result.data]
                    if not model_number:
                        return ChatResponse(
                            assistant_text=(
                                "The ice maker assembly may need replacement. Here are compatible parts. "
                                "**To verify fit**, please share your model number."
                            ),
                            cards=cards,
                            quick_replies=["Share model number", "Where to find model number"],
                        )
                    else:
                        return ChatResponse(
                            assistant_text=(
                                "The ice maker assembly may need replacement. "
                                f"Here are parts (I'll verify fit for {model_number}):"
                            ),
                            cards=cards,
                            quick_replies=[f"Check compatibility for {model_number}"],
                        )

    # Cooling flow
    elif "cooling" in flow_id:
        if step == 1:
            if answer.lower() == "no":
                return ChatResponse(
                    assistant_text=(
                        "If the compressor isn't running, it could be a start relay or compressor issue. "
                        "This usually requires a technician."
                    ),
                    cards=[
                        {
                            "type": "out_of_scope",
                            "id": "oos_cooling",
                            "data": {
                                "reason": "compressor_repair",
                                "message": "Compressor repairs typically require professional service.",
                            },
                        }
                    ],
                    quick_replies=["Find a technician", "Other issues"],
                )
            else:
                return ChatResponse(
                    assistant_text="The compressor is running. Let's check airflow.",
                    cards=[
                        {
                            "type": "troubleshoot_step",
                            "id": f"trouble_{flow_id}_2",
                            "data": {
                                "stepNumber": 2,
                                "totalSteps": 3,
                                "question": "Are the vents inside the fridge blocked by food?",
                                "options": [
                                    {"label": "Yes", "value": "yes"},
                                    {"label": "No", "value": "no"},
                                ],
                                "flowId": flow_id,
                                "symptom": "cooling",
                            },
                        }
                    ],
                )

        elif step == 2:
            if answer.lower() == "yes":
                return ChatResponse(
                    assistant_text=(
                        "Clear the vents to allow proper airflow. "
                        "If that doesn't help, the evaporator fan or defrost system may need attention."
                    ),
                    quick_replies=["Find parts", "More help"],
                )

    # Generic fallback
    return ChatResponse(
        assistant_text=(
            "Based on your responses, I recommend checking these parts. "
            "Would you like me to search for specific components?"
        ),
        quick_replies=["Find a part", "Start over"],
    )

