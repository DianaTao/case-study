"""Agent orchestrator with tool-calling."""
import re
from typing import Dict, Any, Optional, List
import structlog

from models import ChatRequest, ChatResponse
from config import settings

logger = structlog.get_logger()

# Import supported appliances from config
SUPPORTED_APPLIANCES = settings.supported_appliances


class AgentOrchestrator:
    """Main agent that routes intents and executes tools."""
    
    def __init__(self):
        self.llm_client = None
        if settings.openai_api_key:
            from openai import OpenAI
            self.llm_client = OpenAI(api_key=settings.openai_api_key)
    
    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process a user message and return structured response.
        Enforces guardrails: scope gating, required facts, tool verification.
        """
        from database import get_db
        
        message = request.message
        context = request.context or {}
        
        # Fast intent detection (includes entity extraction)
        intent, entities = self._detect_intent(message)
        
        # Use LLM for intent classification when regex might be ambiguous
        # Specifically: distinguish troubleshooting from installation
        if intent in ["install_help", "troubleshoot"]:
            llm_intent = await self._detect_intent_with_llm(message, entities)
            if llm_intent and llm_intent in ["install_help", "troubleshoot", "part_lookup", "compatibility_check"]:
                # LLM overrides regex if they disagree on these key intents
                if llm_intent != intent:
                    print(f"🔄 Intent override: regex={intent} → LLM={llm_intent}")
                    intent = llm_intent
        
        # GUARDRAIL 1: Early scope gate (before any processing)
        if intent == "out_of_scope":
            logger.info("Out of scope request", message=message[:100], entities=entities)
            return self._handle_out_of_scope(entities)
        
        # GUARDRAIL 2: Enforce appliance type detection or existing context
        if not entities.get("appliance_type") and not context.get("appliance"):
            # Check if session has appliance type
            try:
                db = get_db()
                session = db.table("chat_sessions").select("appliance_type").eq(
                    "id", request.session_id
                ).execute()
                if session.data and session.data[0].get("appliance_type"):
                    context["appliance"] = session.data[0]["appliance_type"]
                    entities["appliance_type"] = session.data[0]["appliance_type"]
            except:
                pass
        
        # Update context with detected appliance type
        if entities.get("appliance_type"):
            context["appliance"] = entities["appliance_type"]
            
            # Update session in database with detected appliance type
            try:
                db = get_db()
                db.table("chat_sessions").update({
                    "appliance_type": entities["appliance_type"]
                }).eq("id", request.session_id).execute()
                print(f"✅ Updated session with appliance type: {entities['appliance_type']}")
            except Exception as e:
                logger.warning("Failed to update session appliance type", error=str(e))
        
        # Update context with detected brand
        if entities.get("brand"):
            context["brand"] = entities["brand"]
        
        # Update context with detected model number
        if entities.get("model_number"):
            context["modelNumber"] = entities["model_number"]
        
        logger.info("Detected intent", intent=intent, entities=entities, context=context)
        
        # Route to handler with strict guardrails
        if intent == "part_lookup":
            return await self._handle_part_lookup(message, entities, context, request.session_id)
        elif intent == "compatibility_check":
            # GUARDRAIL: Must have both part AND model
            # CONTEXT FIX: Pass session_id to look back at history
            from . import compatibility_agent
            return await compatibility_agent.handle_compatibility(self, message, entities, context, request.session_id)
        elif intent == "install_help":
            # GUARDRAIL: Must have part number
            # CONTEXT FIX: Pass session_id to look back at history
            from . import install_agent
            return await install_agent.handle_install_help(self, message, entities, request.session_id)
        elif intent == "troubleshoot":
            # GUARDRAIL: Symptom-first flow, not part-first
            from . import troubleshooting_agent
            return await troubleshooting_agent.handle_troubleshoot(self, message, entities, context)
        elif intent == "returns_policy":
            from . import commerce_agent
            return await commerce_agent.handle_returns_policy()
        elif intent in ["cart_update", "cart_remove", "cart_checkout", "cart_view"]:
            # NEW: Cart operations
            from . import commerce_agent
            return await commerce_agent.handle_cart_operation(self, intent, message, entities, context)
        else:
            return await self._handle_general(message, context)
    
    async def _normalize_partial_identifier(self, text: str, id_type: str) -> Dict[str, Any]:
        """
        Handle partial/incomplete identifiers (e.g., "WDT780..." → suggest full models).
        
        Args:
            text: User input containing partial identifier
            id_type: "model" or "part"
        
        Returns:
            {
                "normalized": "WDT780",  # Clean prefix
                "is_complete": False,
                "confidence": 0.6,
                "suggestions": ["WDT780SAEM1", "WDT780PAEM1"]
            }
        """
        from database import get_db
        
        if id_type == "model":
            # Extract clean prefix (handle ellipsis, spaces, etc.)
            clean_text = re.sub(r'[.\s…]+', '', text.upper())
            match = re.search(r'([A-Z]{2,}[0-9]{3,}[A-Z0-9]*)', clean_text)
            
            if match:
                prefix = match.group(1)
                
                # Consider complete if: 2+ letters, 3+ digits, 2+ suffix chars
                is_complete = bool(re.match(r'^[A-Z]{2,}[0-9]{3,}[A-Z0-9]{2,}$', prefix))
                
                if not is_complete:
                    # Search database for models starting with this prefix
                    try:
                        db = get_db()
                        result = db.table("models").select("model_number").ilike(
                            "model_number", f"{prefix}%"
                        ).limit(5).execute()
                        
                        suggestions = [m["model_number"] for m in result.data] if result.data else []
                        
                        print(f"🔍 Partial model number '{prefix}' → Found {len(suggestions)} suggestions")
                        
                        return {
                            "normalized": prefix,
                            "is_complete": False,
                            "confidence": 0.6,
                            "suggestions": suggestions
                        }
                    except Exception as e:
                        print(f"⚠️  Model search failed: {e}")
                        return {
                            "normalized": prefix,
                            "is_complete": False,
                            "confidence": 0.5,
                            "suggestions": []
                        }
                
                # Model looks complete
                return {
                    "normalized": prefix,
                    "is_complete": True,
                    "confidence": 0.9,
                    "suggestions": []
                }
        
        return {"normalized": None, "is_complete": False, "confidence": 0, "suggestions": []}
    
    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """
        Extract entities from natural language using robust regex patterns:
        - Appliance type (refrigerator/dishwasher)
        - Brand (Whirlpool, GE, Frigidaire, etc.)
        - Part/component (ice maker, water filter, etc.)
        - Part number (PS\d{6,9} per PartSelect format)
        - Model number (validated alphanumeric 5-15 chars)
        - Symptoms (for troubleshooting)
        """
        lower_msg = message.lower()
        entities = {}
        
        # Appliance type detection
        appliance_patterns = {
            "refrigerator": [
                r'\brefrigerator\b', r'\bfridge\b', r'\bfreezer\b', 
                r'\bice maker\b', r'\bwater filter\b', r'\bcrisper\b',
                r'\bdoor shelf\b', r'\bcooling\b', r'\bice\b'
            ],
            "dishwasher": [
                r'\bdishwasher\b', r'\bspray arm\b', r'\brack\b',
                r'\bdetergent dispenser\b', r'\bdrain pump\b', r'\bheating element\b',
                r'\bdishes\b', r'\bwashing\b'
            ]
        }
        
        for appliance, patterns in appliance_patterns.items():
            if any(re.search(pattern, lower_msg) for pattern in patterns):
                entities["appliance_type"] = appliance
                print(f"🔍 Detected appliance: {appliance}")
                break
        
        # Brand detection (using \b for word boundaries)
        brand_patterns = [
            r'\b(whirlpool)\b', r'\b(ge)\b', r'\b(frigidaire)\b', 
            r'\b(samsung)\b', r'\b(lg)\b', r'\b(kenmore)\b',
            r'\b(maytag)\b', r'\b(kitchenaid)\b', r'\b(bosch)\b',
            r'\b(amana)\b', r'\b(electrolux)\b'
        ]
        
        for pattern in brand_patterns:
            match = re.search(pattern, lower_msg, re.IGNORECASE)
            if match:
                brand_name = match.group(1)
                # Special case for GE (all caps)
                if brand_name.lower() == "ge":
                    entities["brand"] = "GE"
                else:
                    entities["brand"] = brand_name.capitalize()
                print(f"🔍 Detected brand: {entities['brand']}")
                break
        
        # Part/component detection (expanded)
        part_keywords = {
            "ice maker": ["ice maker", "icemaker", "ice machine", "ice dispenser"],
            "water filter": ["water filter", "filter", "water filtration"],
            "door shelf": ["door shelf", "door bin", "shelf bin", "door bucket"],
            "crisper drawer": ["crisper", "crisper drawer", "vegetable drawer", "produce drawer"],
            "door seal": ["door seal", "door gasket", "gasket"],
            "heating element": ["heating element", "heater", "heat element"],
            "spray arm": ["spray arm", "wash arm", "sprayer"],
            "drain pump": ["drain pump", "pump", "drainage pump"],
            "motor": ["motor", "fan motor"],
            "compressor": ["compressor"],
            "thermostat": ["thermostat"],
            "defrost": ["defrost", "defrost timer", "defrost heater"],
        }
        
        for part_name, keywords in part_keywords.items():
            if any(kw in lower_msg for kw in keywords):
                entities["part_component"] = part_name
                print(f"🔍 Detected part: {part_name}")
                break
        
        # Extract PartSelect number (PS\d{6,9} per PartSelect format)
        part_match = re.search(r'\bPS(\d{6,9})\b', message, re.IGNORECASE)
        if part_match:
            entities["part_number"] = f"PS{part_match.group(1)}"
            print(f"🔍 Detected part number: {entities['part_number']}")
        
        # Extract model number (validated: 5-15 chars, alphanumeric, must have digit)
        # Look for candidates
        model_candidates = re.findall(r'\b([A-Z0-9]{5,15})\b', message, re.IGNORECASE)
        for candidate in model_candidates:
            candidate_upper = candidate.upper()
            # Must contain at least one digit
            if not re.search(r'\d', candidate_upper):
                continue
            # Skip common words
            if candidate_upper in {'YES', 'NO', 'HELP', 'TRUE', 'FALSE', 'ERROR'}:
                continue
            # Skip if it's a PartSelect number
            if candidate_upper.startswith('PS') and re.match(r'PS\d{6,9}', candidate_upper):
                continue
            # This looks like a model number
            entities["model_number"] = candidate_upper
            print(f"🔍 Detected model: {entities['model_number']}")
            break
        
        # Symptom extraction (for troubleshooting)
        symptom_patterns = {
            "not working": r'\b(not working|won\'t work|doesn\'t work|stopped working)\b',
            "not cooling": r'\b(not cooling|warm|not cold|too warm)\b',
            "not making ice": r'\b(not making ice|no ice|ice maker not working)\b',
            "leaking": r'\b(leak|leaking|dripping|water on floor)\b',
            "not draining": r'\b(not draining|won\'t drain|standing water|water in bottom)\b',
            "not cleaning": r'\b(not cleaning|dishes dirty|not washing|won\'t clean)\b',
            "not drying": r'\b(not drying|wet dishes|won\'t dry)\b',
            "noisy": r'\b(noisy|loud|grinding|squeaking)\b',
            "not starting": r'\b(won\'t start|not starting|doesn\'t start)\b',
        }
        
        detected_symptoms = []
        for symptom_name, pattern in symptom_patterns.items():
            if re.search(pattern, lower_msg):
                detected_symptoms.append(symptom_name)
        
        if detected_symptoms:
            entities["symptoms"] = detected_symptoms
            print(f"🔍 Detected symptoms: {', '.join(detected_symptoms)}")
        
        return entities
    
    async def _detect_intent_with_llm(self, message: str, entities: Dict) -> Optional[str]:
        """
        Use OpenAI for intent classification when regex is ambiguous.
        Returns intent string or None if OpenAI fails.
        """
        try:
            import openai
            from config import settings
            
            prompt = f"""You are an intent classifier for an appliance parts assistant.

User message: "{message}"

Detected entities: {entities}

Classify the user's intent into ONE of these categories:
1. "install_help" - User wants installation instructions (e.g., "how do I install", "how to replace")
2. "troubleshoot" - User has a problem and needs help fixing it (e.g., "not working", "won't start", "leaking")
3. "part_lookup" - User wants to find or learn about a part (e.g., "what is PS####", "find a part")
4. "compatibility_check" - User wants to verify if a part fits their model (e.g., "compatible with", "will it fit")
5. "general" - General question or greeting

Rules:
- If message contains a problem/symptom (not working, broken, leaking, etc.) → "troubleshoot"
- If message asks "how to install/replace" → "install_help"
- If message asks about compatibility/fit → "compatibility_check"
- If message just mentions a part number without action → "part_lookup"

Respond with ONLY the intent name, nothing else."""

            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an intent classifier. Respond with only the intent name."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            llm_intent = response.choices[0].message.content.strip().lower()
            print(f"🤖 LLM intent: {llm_intent}")
            return llm_intent
            
        except Exception as e:
            print(f"⚠️  LLM intent classification failed: {e}")
            return None
    
    def _detect_intent(self, message: str) -> tuple[str, Dict[str, Any]]:
        """
        Fast heuristic-based intent detection with entity extraction.
        GUARDRAIL: Early out-of-scope detection before any processing.
        """
        lower_msg = message.lower()
        
        # GUARDRAIL 1: Detect explicitly out-of-scope appliances (oven, microwave, washer, dryer)
        out_of_scope_appliances = [
            "oven", "stove", "range", "microwave", "washer", "washing machine",
            "dryer", "clothes dryer", "freezer", "wine cooler", "ice maker"
        ]
        if any(appliance in lower_msg for appliance in out_of_scope_appliances):
            # Check if they're also mentioning fridge/dishwasher (might be comparing)
            if not any(kw in lower_msg for kw in ["refrigerator", "fridge", "dishwasher"]):
                return "out_of_scope", {"detected_appliance": next(a for a in out_of_scope_appliances if a in lower_msg)}
        
        # Extract all entities
        entities = self._extract_entities(message)
        
        # Intent patterns (order matters! Check specific intents before general ones)
        
        # 1. Install intent (check BEFORE part_lookup to catch "how to install PS####")
        if re.search(r'\b(install|installation|replace|replacement|how do i|how can i|how to)\b', lower_msg):
            return "install_help", entities
        
        # 2. Compatibility check
        if re.search(r'\b(compatible|compatibility|check compatibility|check fit|fit|fits|work with)\b', lower_msg):
            return "compatibility_check", entities
        
        # 3. Part lookup (general - only if no specific intent above)
        if entities.get("part_number") or re.search(r'\bpart number\b', lower_msg):
            return "part_lookup", entities

        if re.search(r'\b(find a part|find part|search parts|lookup part|part lookup)\b', lower_msg):
            return "part_lookup", entities
        
        # CONTEXT FIX: Detect troubleshooting or appliance selection in troubleshooting context
        if re.search(r'\b(troubleshoot|not working|broken|problem|issue|fix|repair)\b', lower_msg):
            return "troubleshoot", entities
        
        # CONTEXT FIX: If message is just an appliance type, treat as troubleshoot intent
        if lower_msg.strip() in ["refrigerator", "dishwasher", "fridge"] and entities.get("appliance_type"):
            return "troubleshoot", entities
        
        if re.search(r'\b(return|refund|policy)\b', lower_msg):
            return "returns_policy", entities
        
        # NEW: Cart operations (quantity updates, removal, checkout)
        if re.search(r'\b(make that|change to|update to|change quantity|update quantity)\s*(\d+)\b', lower_msg):
            return "cart_update", entities
        
        if re.search(r'\b(remove|delete|take out).*(from cart|from my cart)\b', lower_msg):
            return "cart_remove", entities
        
        if re.search(r'\b(checkout|check out|purchase|buy now|proceed to checkout)\b', lower_msg):
            return "cart_checkout", entities
        
        if re.search(r'\b(view cart|show cart|my cart|what.*in.*cart)\b', lower_msg):
            return "cart_view", entities
        
        # GUARDRAIL 2: Check if in-scope (config-based supported appliances)
        in_scope = entities.get("appliance_type") in SUPPORTED_APPLIANCES
        
        if not in_scope:
            # Double-check with keywords
            in_scope_keywords = [
                "refrigerator", "fridge", "dishwasher", "part", "model",
                "ice maker", "water filter", "door seal", "pump", "motor",
                "spray arm", "crisper", "shelf", "rack", "heating element"
            ]
            in_scope = any(kw in lower_msg for kw in in_scope_keywords)
        
        # CONTEXT FIX: If we extracted a model number, assume it's in-scope
        # (User is likely providing model for compatibility check)
        if not in_scope and entities.get("model_number"):
            print(f"🔍 Treating as in-scope due to model number: {entities.get('model_number')}")
            in_scope = True
            # Treat as compatibility check since they provided a model number
            return "compatibility_check", entities
        
        if not in_scope:
            return "out_of_scope", entities
        
        return "general", entities
    
    async def _handle_part_lookup(
        self,
        message: str,
        entities: Dict,
        context: Dict,
        session_id: str
    ) -> ChatResponse:
        """Handle part lookup requests."""
        from database import get_db
        
        db = get_db()
        part_number = entities.get("part_number")
        
        if part_number:
            # Direct lookup
            result = db.table("parts").select("*").eq(
                "partselect_number", part_number
            ).execute()
            
            if result.data:
                part = result.data[0]
                
                # If price is missing, try to fetch it dynamically
                if part.get("price_cents") is None or part.get("stock_status") == "unknown":
                    product_url = part.get("canonical_url") or part.get("product_url")
                    if product_url:
                        try:
                            print(f"💰 Fetching price for {part_number}...")
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
                                db.table("parts").update({
                                    "price_cents": price_cents,
                                    "stock_status": availability
                                }).eq("partselect_number", part_number).execute()
                            else:
                                print(f"⚠️  No price found")
                        except Exception as e:
                            print(f"⚠️  Price fetch failed: {e}")
                
                return ChatResponse(
                    assistant_text=f"Here's the information for {part['name']}:",
                    cards=[self._create_product_card(part)],
                    quick_replies=["Check compatibility", "Installation instructions", "Add to cart"]
                )
            else:
                canonical_url = f"https://www.partselect.com/Search.aspx?SearchTerm={part_number}"
                return ChatResponse(
                    assistant_text=(
                        f"I don't have {part_number} in the seed catalog yet. "
                        "You can verify it directly on PartSelect, and I can still help with fit checks."
                    ),
                    cards=[{
                        "type": "product",
                        "id": f"product_{part_number}",
                        "data": {
                            "title": f"PartSelect result for {part_number}",
                            "price": None,
                            "currency": "USD",
                            "inStock": None,
                            "partselectNumber": part_number,
                            "manufacturerPartNumber": None,
                            "rating": None,
                            "reviewCount": 0,
                            "imageUrl": None,
                            "productUrl": canonical_url,
                            "install": {
                                "hasInstructions": False,
                                "hasVideos": False,
                                "links": []
                            },
                            "cta": {
                                "action": "view_details",
                                "payload": {"url": canonical_url}
                            }
                        }
                    }],
                    quick_replies=["Check compatibility", "Search another part"]
                )
        else:
            # CONTEXT FIX: Look back at conversation history for search context
            search_text = message
            historical_context = None
            
            if re.search(r'\b(find a part|find part|search parts|lookup part|part lookup)\b', message.lower()):
                history = db.table("chat_messages").select("content").eq(
                    "session_id", session_id
                ).eq("role", "user").order("created_at", desc=True).limit(10).execute()
                
                print(f"\n🔍 Looking back at conversation history for context...")
                
                if history.data:
                    for item in history.data:
                        content = item.get("content", "").strip()
                        if not content:
                            continue
                        if content.lower().startswith("answer:"):
                            continue
                        if re.search(r'\b(find a part|find part|search parts|lookup part|part lookup)\b', content.lower()):
                            continue
                        if len(content) < 8:
                            continue
                        
                        # CONTEXT FIX: Extract entities from historical message
                        historical_entities = self._extract_entities(content)
                        print(f"   Found historical message: {content[:60]}...")
                        print(f"   Extracted entities: {historical_entities}")
                        
                        search_text = content
                        historical_context = historical_entities
                        break

            # CONTEXT FIX: Use extracted entities from history for better search
            appliance_type = context.get("appliance") or (historical_context or {}).get("appliance_type")
            part_component = (historical_context or {}).get("part_component")
            
            # Build search terms from context
            fallback_terms = [
                "ice maker", "water filter", "door shelf", "crisper drawer",
                "spray arm", "dishrack wheel", "rack adjuster", "heating element"
            ]
            
            # Prioritize extracted part component
            if part_component:
                terms = [part_component]
                print(f"   Using part component from context: {part_component}")
            else:
                terms = [term for term in fallback_terms if term in search_text.lower()]
                if not terms:
                    terms = fallback_terms[:3]

            or_filters = ",".join([f"name.ilike.%{term}%" for term in terms])
            query = db.table("parts").select("*").or_(or_filters)
            
            # GUARDRAIL: Hard filter by appliance type
            if appliance_type:
                query = query.eq("appliance_type", appliance_type)
                print(f"   Hard filter: appliance_type = {appliance_type}")
            
            result = query.limit(5).execute()
            
            if result.data:
                cards = [self._create_product_card(part) for part in result.data]
                return ChatResponse(
                    assistant_text=f"I found {len(result.data)} parts matching your search:",
                    cards=cards,
                    quick_replies=["Check fit", "More details"]
                )
            else:
                return ChatResponse(
                    assistant_text="I couldn't find any parts matching your search. Could you provide more details or a specific part number?",
                    cards=[]
                )
    
    async def _handle_compatibility(self, message: str, entities: Dict, context: Dict, session_id: str = None) -> ChatResponse:
        """
        Handle compatibility checks with strict guardrails.
        MUST have both part number AND model number to proceed.
        Never guesses or assumes compatibility - tool-verified only.
        """
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
                    historical_entities = self._extract_entities(content)
                    if historical_entities.get("part_number"):
                        part_number = historical_entities["part_number"]
                        print(f"   Found part number in history: {part_number}")
                        break
        
        # GUARDRAIL: Must have part number
        if not part_number:
            return ChatResponse(
                assistant_text="To check compatibility, I need the part number. Please provide the PartSelect number (PS####) or share the product link.",
                cards=[],
                quick_replies=["Example: PS11701542", "Share PartSelect link"]
            )
        
        # GUARDRAIL: Must have model number - use refined model_capture card
        if not model_number:
            return ChatResponse(
                version="1.1",
                intent="compatibility_check",
                source="rules",
                assistant_text="To be sure, I need your appliance model number.",
                cards=[{
                    "type": "model_capture",
                    "id": "model_capture_1",
                    "data": {
                        "title": "What's your model number?",
                        "body": "You can usually find this on a sticker inside the door or on the frame.",
                        "canSkip": True,
                        "reason": "compatibility_check"
                    }
                }],
                quick_replies=["I don't know", "Skip for now"]
            )
        
        # NEW: Check if model number is complete (handle "WDT780..." scenarios)
        normalized_result = await self._normalize_partial_identifier(model_number, "model")
        
        if not normalized_result["is_complete"] and normalized_result["suggestions"]:
            # Model number looks incomplete - ask for clarification
            suggestions = normalized_result["suggestions"][:3]
            return ChatResponse(
                assistant_text=(
                    f"I found your model prefix **{normalized_result['normalized']}**, but I need the full model number to verify compatibility. "
                    f"Did you mean one of these?"
                ),
                cards=[],
                quick_replies=suggestions + ["I'll check my appliance label"]
            )
        elif not normalized_result["is_complete"] and not normalized_result["suggestions"]:
            # Incomplete and no suggestions - ask user to verify
            return ChatResponse(
                assistant_text=(
                    f"The model number **{model_number}** looks incomplete. "
                    f"Can you check the full model number on your appliance? It's usually 8-12 characters (e.g., WDT780SAEM1)."
                ),
                cards=[],
                quick_replies=["Where's my model number?"]
            )
        
        # GUARDRAIL: Tool-verified compatibility check (no guessing)
        normalized_model = normalized_result["normalized"] or model_number.upper().replace(" ", "").replace("-", "")
        
        # Check if part exists first
        part_result = db.table("parts").select("appliance_type, name").eq(
            "partselect_number", part_number
        ).execute()
        
        if not part_result.data:
            return ChatResponse(
                assistant_text=f"I don't have part {part_number} in my catalog. Please verify the part number or share the PartSelect product link.",
                cards=[],
                quick_replies=["Search for parts"]
            )
        
        part = part_result.data[0]
        
        # Check compatibility in database first
        result = db.table("model_parts").select("*").eq(
            "partselect_number", part_number
        ).eq("model_number", normalized_model).execute()
        
        if result.data and result.data[0].get("confidence") == "exact":
            # VERIFIED COMPATIBILITY (from database)
            record = result.data[0]
            return ChatResponse(
                assistant_text=f"✅ **Verified**: Part {part_number} ({part['name']}) is confirmed compatible with model {model_number}.",
                cards=[{
                    "type": "compatibility",
                    "id": "compat_1",
                    "data": {
                        "status": "fits",
                        "partselect_number": part_number,
                        "model_number": model_number,
                        "reason": f"This part is confirmed compatible with model {model_number}.",
                        "evidence": {
                            "url": record.get("evidence_url"),
                            "snippet": record.get("evidence_snippet")
                        }
                    }
                }],
                quick_replies=["Add to cart", "Installation help"]
            )
        
        # Database didn't have info - try cross-brand compatibility first (NEW!)
        print(f"\n🔧 Database has no compatibility data. Checking cross-brand compatibility...")
        
        # Get full part details
        full_part_result = db.table("parts").select("*").eq(
            "partselect_number", part_number
        ).execute()
        
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
                    detected_brand=detected_brand
                )
                
                if cross_brand_result["is_compatible"] is True:
                    # Cross-brand match found!
                    return ChatResponse(
                        assistant_text=(
                            f"✅ **Cross-Brand Match**: {cross_brand_result['reason']}\n\n"
                            f"*Confidence: {int(cross_brand_result['confidence'] * 100)}%*"
                        ),
                        cards=[{
                            "type": "compatibility",
                            "id": "compat_cross_brand",
                            "data": {
                                "status": "fits",
                                "partselect_number": part_number,
                                "model_number": model_number,
                                "reason": cross_brand_result['reason'],
                                "confidence": "high"
                            }
                        }],
                        quick_replies=["Add to cart", "Installation help", "View on PartSelect"]
                    )
                elif cross_brand_result["is_compatible"] is False:
                    # Definitely not compatible due to cross-brand rules
                    return ChatResponse(
                        assistant_text=(
                            f"❌ **Not Compatible**: {cross_brand_result['reason']}\n\n"
                            f"*Confidence: {int(cross_brand_result['confidence'] * 100)}%*"
                        ),
                        cards=[{
                            "type": "compatibility",
                            "id": "compat_not_cross_brand",
                            "data": {
                                "status": "does_not_fit",
                                "partselect_number": part_number,
                                "model_number": model_number,
                                "reason": cross_brand_result['reason'],
                                "confidence": "high"
                            }
                        }],
                        quick_replies=["Search for compatible parts"]
                    )
                else:
                    print(f"   ⚠️  Cross-brand check inconclusive: {cross_brand_result['reason']}")
        
        # Cross-brand didn't help - try dynamic scraping
        print(f"\n🔧 Attempting dynamic scraping...")
        
        if full_part_result.data:
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
                        user_model=model_number
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
                                cards=[{
                                    "type": "compatibility",
                                    "id": "compat_scraped",
                                    "data": {
                                        "status": "fits",
                                        "partselect_number": part_number,
                                        "model_number": model_number,
                                        "reason": reason,
                                        "confidence": confidence
                                    }
                                }],
                                quick_replies=["Add to cart", "Installation help", "Verify on PartSelect"]
                            )
                        else:
                            # NOT COMPATIBLE
                            return ChatResponse(
                                assistant_text=(
                                    f"❌ **Not Compatible**: Part {part_number} ({part['name']}) does not appear to be compatible with model {model_number}.\n\n"
                                    f"**Reason:** {reason}\n\n"
                                    f"*Confidence: {confidence.capitalize()}*"
                                ),
                                cards=[{
                                    "type": "compatibility",
                                    "id": "compat_not_fit",
                                    "data": {
                                        "status": "does_not_fit",
                                        "partselect_number": part_number,
                                        "model_number": model_number,
                                        "reason": reason,
                                        "confidence": confidence
                                    }
                                }],
                                quick_replies=["Search for compatible parts", "Verify on PartSelect"]
                            )
                
                except Exception as e:
                    print(f"⚠️  Compatibility scraping failed: {e}")
                    compat_result = None
        
        # If scraping found replacement parts but couldn't determine compatibility
        if compat_result and compat_result.get("replaces") and compat_result.get("compatible") is None:
            replaces_list = compat_result["replaces"][:10]  # Show first 10
            part_url = product_url or f"https://www.partselect.com/Search.aspx?SearchTerm={part_number}"
            
            return ChatResponse(
                assistant_text=(
                    f"⚠️ I cannot definitively verify compatibility for part {part_number} with model {model_number} based on available data.\n\n"
                    f"**Alternative Part Numbers:**\n"
                    f"This part replaces these manufacturer part numbers:\n"
                    f"{', '.join(replaces_list)}\n\n"
                    f"If your appliance uses any of these part numbers, this part should be compatible. "
                    f"Otherwise, please verify on PartSelect using their model lookup tool."
                ),
                cards=[{
                    "type": "compatibility",
                    "id": "compat_uncertain",
                    "data": {
                        "status": "need_info",
                        "partselect_number": part_number,
                        "model_number": model_number,
                        "reason": f"This part replaces: {', '.join(replaces_list[:5])}...",
                        "verifyUrl": part_url
                    }
                }],
                quick_replies=["Verify on PartSelect", "Search other parts"]
            )
        
        # Fallback: CANNOT VERIFY (no data at all)
        part_url = f"https://www.partselect.com/Search.aspx?SearchTerm={part_number}"
        return ChatResponse(
            assistant_text=(
                f"⚠️ I cannot verify compatibility for part {part_number} with model {model_number}. "
                f"Please verify directly on PartSelect using their model lookup tool to ensure this part fits your specific appliance."
            ),
            cards=[{
                "type": "compatibility",
                "id": "compat_1",
                "data": {
                    "status": "need_info",
                    "partselect_number": part_number,
                    "model_number": model_number,
                    "reason": "Compatibility data not available in our database. Manual verification required.",
                    "verifyUrl": part_url
                }
            }],
            quick_replies=["Verify on PartSelect", "Search other parts"]
        )
    
    async def _handle_install_help(self, message: str, entities: Dict, session_id: str = None) -> ChatResponse:
        """
        Handle installation help requests.
        GUARDRAIL: Must have part number to provide installation guidance.
        """
        from database import get_db
        
        db = get_db()
        part_number = entities.get("part_number")
        
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
                    historical_entities = self._extract_entities(content)
                    if historical_entities.get("part_number"):
                        part_number = historical_entities["part_number"]
                        print(f"   Found part number in history: {part_number}")
                        break
        
        # GUARDRAIL: Must have part number
        if not part_number:
            return ChatResponse(
                assistant_text="Which part do you need installation help with? Please provide the PartSelect number (PS####) or product link.",
                cards=[],
                quick_replies=["Example: PS11701542", "Share product link"]
            )
        
        db = get_db()
        result = db.table("parts").select("*").eq("partselect_number", part_number).execute()
        
        if not result.data:
            return ChatResponse(
                assistant_text=f"I couldn't find part {part_number}.",
                cards=[]
            )
        
        part = result.data[0]
        part_name = part['name'].lower()
        product_url = part.get("canonical_url") or part.get("product_url")
        
        # GUARDRAIL: Product-specific installation guidance
        # Try dynamic scraping first if we have a URL
        install_instructions = None
        
        if product_url:
            print(f"\n🔧 Attempting to scrape installation instructions from {product_url}")
            try:
                from services.install_scraper import extract_install_instructions
                install_instructions = await extract_install_instructions(
                    url=product_url,
                    part_name=part['name'],
                    part_number=part_number
                )
            except Exception as e:
                print(f"⚠️  Install scraping failed: {e}")
                install_instructions = None
        
        # If scraping succeeded, return those instructions WITH product card
        if install_instructions:
            # If price is missing, try to fetch it dynamically
            if part.get("price_cents") is None or part.get("stock_status") == "unknown":
                if product_url:
                    try:
                        print(f"💰 Fetching price for {part_number}...")
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
                            db.table("parts").update({
                                "price_cents": price_cents,
                                "stock_status": availability
                            }).eq("partselect_number", part_number).execute()
                    except Exception as e:
                        print(f"⚠️  Price fetch failed: {e}")
            
            # Create product card for context
            product_card = self._create_product_card(part)
            
            return ChatResponse(
                assistant_text=f"Here's how to install **{part['name']}**:\n\n{install_instructions}",
                cards=[product_card],  # Include product card with instructions
                quick_replies=["View full instructions on PartSelect", "Add to cart", "Check compatibility"]
            )
        
        # Fall back to stored install_summary if available
        install_summary = part.get("install_summary")
        
        if install_summary:
            # If price is missing, try to fetch it dynamically
            if part.get("price_cents") is None or part.get("stock_status") == "unknown":
                if product_url:
                    try:
                        print(f"💰 Fetching price for {part_number}...")
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
                            db.table("parts").update({
                                "price_cents": price_cents,
                                "stock_status": availability
                            }).eq("partselect_number", part_number).execute()
                    except Exception as e:
                        print(f"⚠️  Price fetch failed: {e}")
            
            # We have product-specific instructions from seed data
            product_card = self._create_product_card(part)
            
            return ChatResponse(
                assistant_text=f"Here's how to install {part['name']}:\n\n{install_summary}",
                cards=[product_card],  # Include product card with instructions
                quick_replies=["View full instructions on PartSelect", "Add to cart", "Check compatibility"]
            )
        
        # GUARDRAIL: If no product-specific instructions, link out instead of inventing steps
        # Detect simple parts that don't need power disconnection
        simple_parts = ["shelf", "bin", "drawer", "rack", "knob", "handle", "cover", "cap", "trim"]
        is_simple_part = any(keyword in part_name for keyword in simple_parts)
        
        if is_simple_part:
            return ChatResponse(
                assistant_text=(
                    f"**{part['name']}** is typically a simple snap-in or tool-free installation. "
                    f"For product-specific instructions, diagrams, and videos, please visit the PartSelect product page."
                ),
                cards=[{
                    "type": "out_of_scope",
                    "id": "install_link_out",
                    "data": {
                        "message": f"Installation instructions for {part_number}",
                        "suggestedActions": [
                            "View instructions on PartSelect",
                            "Watch installation videos",
                            "Check compatibility"
                        ]
                    }
                }],
                quick_replies=[
                    "View on PartSelect" if product_url else None,
                    "Add to cart",
                    "Check compatibility"
                ]
            )
        else:
            # For electrical/mechanical parts, link out for safety
            return ChatResponse(
                assistant_text=(
                    f"**{part['name']}** installation requires careful attention to safety and proper procedures. "
                    f"For detailed product-specific instructions, safety warnings, diagrams, and videos, "
                    f"please visit the PartSelect product page."
                ),
                cards=[{
                    "type": "out_of_scope",
                    "id": "install_link_out",
                    "data": {
                        "message": f"Installation instructions for {part_number}",
                        "suggestedActions": [
                            "View instructions on PartSelect",
                            "Watch installation videos",
                            "Check compatibility"
                        ]
                    }
                }],
                quick_replies=[
                    "View on PartSelect" if product_url else None,
                    "Add to cart",
                    "Check compatibility"
                ]
            )
    
    async def _handle_troubleshoot(self, message: str, entities: Dict, context: Dict) -> ChatResponse:
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
                quick_replies=["Refrigerator", "Dishwasher"]
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
                        "Other issue"
                    ]
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
                        "Other issue"
                    ]
                )
        
        # Try intelligent symptom-based part recommendations using OpenAI + scraped data
        try:
            symptom_guidance = await self._get_symptom_guidance_with_llm(
                message=message,
                appliance_type=appliance_type,
                detected_symptoms=detected_symptoms
            )
            
            if symptom_guidance:
                return symptom_guidance
        except Exception as e:
            print(f"⚠️  Symptom guidance LLM failed: {e}")
        
        # Fallback: Detect specific symptoms and route to appropriate flows
        symptom_map = {
            "ice maker": {
                "keywords": ["ice maker", "ice", "not making ice", "no ice"],
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
            
            all_matching_parts = []
            for symptom in detected_symptoms:
                # GUARDRAIL: Hard filter by appliance_type to prevent category leakage
                parts = await self._search_parts_by_symptom(symptom, appliance_type)
                all_matching_parts.extend(parts)
            
            # De-duplicate parts
            seen = set()
            unique_parts = []
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
                
                cards = [self._create_product_card(part) for part in unique_parts[:5]]
                symptom_text = ", ".join(detected_symptoms)
                
                if not model_number:
                    return ChatResponse(
                        assistant_text=(
                            f"Based on the symptom '{symptom_text}', here are parts that commonly fix this issue. "
                            f"**To verify fit**, please share your appliance's model number (found on a label inside the door or on the back)."
                        ),
                        cards=cards,
                        quick_replies=["Share model number", "Where to find model number"]
                    )
                else:
                    return ChatResponse(
                        assistant_text=(
                            f"Based on the symptom '{symptom_text}', here are parts that commonly fix this issue for {appliance_type}s. "
                            f"I'll verify compatibility with your model {model_number}."
                        ),
                        cards=cards,
                        quick_replies=[f"Check fit for {model_number}", "Troubleshoot step-by-step"]
                    )
        
        # Fallback: Match symptom to predefined flow
        detected_symptom = None
        for symptom, config in symptom_map.items():
            if any(kw in lower_msg for kw in config["keywords"]):
                detected_symptom = config
                break
        
        # If no specific symptom, use generic flow
        if not detected_symptom:
            return ChatResponse(
                assistant_text="Let me help you troubleshoot. I'll ask a few questions to narrow down the problem.",
                cards=[{
                    "type": "troubleshoot_step",
                    "id": "trouble_generic_1",
                    "data": {
                        "stepNumber": 1,
                        "totalSteps": 3,
                        "question": "Is the appliance receiving power?",
                        "options": [
                            {"label": "Yes", "value": "yes"},
                            {"label": "No", "value": "no"}
                        ],
                        "flowId": "generic_power",
                        "symptom": "generic"
                    }
                }],
                quick_replies=["Need a part"]
            )
        
        # Return symptom-specific first question
        print(f"\n🔍 Detected symptom flow: {detected_symptom.get('flow')}")
        print(f"   Initial question: {detected_symptom.get('initial_question')}\n")
        
        return ChatResponse(
            assistant_text=f"Let me help you troubleshoot. I'll ask a few targeted questions.",
            cards=[{
                "type": "troubleshoot_step",
                "id": f"trouble_{detected_symptom['flow']}_1",
                "data": {
                    "stepNumber": 1,
                    "totalSteps": 3,
                    "question": detected_symptom["initial_question"],
                    "options": [
                        {"label": "Yes", "value": "yes"},
                        {"label": "No", "value": "no"}
                    ],
                    "flowId": detected_symptom["flow"],
                    "symptom": detected_symptom["flow"],
                    "recommendedParts": detected_symptom.get("parts", [])
                }
            }],
            quick_replies=["Skip to parts"]
        )
    
    async def _handle_troubleshoot_answer(
        self,
        flow_id: str,
        answer: str,
        step: int,
        context: Dict,
    ) -> ChatResponse:
        """Delegate troubleshoot answer handling to troubleshooting_agent."""
        from . import troubleshooting_agent

        return await troubleshooting_agent.handle_troubleshoot_answer(
            self, flow_id, answer, step, context
        )
    
    async def _handle_returns_policy(self) -> ChatResponse:
        """Handle returns policy requests."""
        policy_text = """PartSelect offers a 365-day return policy on most parts. Returns are accepted for:
- Unused parts in original packaging
- Parts that don't fit (with proof of purchase)
- Defective parts

To initiate a return:
1. Contact customer service within 365 days
2. Provide order number and reason
3. Receive return authorization
4. Ship part back with tracking

Refunds are processed within 5-7 business days after receiving the return."""
        
        return ChatResponse(
            assistant_text=policy_text,
            quick_replies=["Start return", "Contact support"]
        )
    
    def _handle_out_of_scope(self, entities: Optional[Dict] = None) -> ChatResponse:
        """
        Handle out-of-scope requests with specific rejection messages.
        GUARDRAIL: Clear scope boundaries - refrigerator and dishwasher only.
        REFINED: Returns OutOfScopeCard with example queries.
        """
        entities = entities or {}
        detected_appliance = entities.get("detected_appliance")
        
        # Provide specific message for detected wrong appliance
        if detected_appliance:
            assistant_text = (
                f"I'm focused on refrigerator and dishwasher parts right now. "
                f"I can't help with {detected_appliance} parts or issues."
            )
        else:
            assistant_text = (
                "I'm focused on refrigerator and dishwasher parts right now."
            )
        
        return ChatResponse(
            version="1.1",
            intent="out_of_scope",
            source="rules",
            assistant_text=assistant_text,
            cards=[{
                "type": "out_of_scope",
                "id": "oos_1",
                "data": {
                    "message": "I can help you find parts, check compatibility, and troubleshoot issues for fridges and dishwashers.",
                    "exampleQueries": [
                        "The ice maker on my Whirlpool fridge is not working",
                        "Is PS11752778 compatible with WDT780SAEM1?",
                        "How can I install part PS11752778?"
                    ]
                }
            }],
            quick_replies=["Find refrigerator parts", "Find dishwasher parts", "Troubleshoot issue"]
        )
    
    async def _handle_general(self, message: str, context: Dict) -> ChatResponse:
        """
        Handle general queries with intelligent clarification.
        GUARDRAIL: Only show main menu if truly starting fresh, not after every interaction.
        ENHANCEMENT: Detects ambiguous prompts and guides user efficiently.
        """
        lower_msg = message.lower()
        entities = self._extract_entities(message)
        
        # CONTEXT FIX: Handle model number location question
        if "where" in lower_msg and "model number" in lower_msg:
            return ChatResponse(
                assistant_text=(
                    "Your appliance's model number is typically located:\n\n"
                    "**For Refrigerators:**\n"
                    "• Inside the fresh food compartment, on the upper left or right wall\n"
                    "• On a label inside the door\n"
                    "• On the back of the unit\n\n"
                    "**For Dishwashers:**\n"
                    "• On the door frame (visible when door is open)\n"
                    "• On the top or side of the door panel\n"
                    "• Inside on the door or tub edge\n\n"
                    "The model number is usually a combination of letters and numbers, like WRF555SDFZ or WDT780SAEM1."
                ),
                cards=[],
                quick_replies=["I have my model number", "Check compatibility"]
            )
        
        # NEW: Detect ambiguous prompts like "I need a replacement shelf"
        ambiguous_patterns = {
            "replacement": r'\b(need|want|looking for|replace|replacement)\b',
            "broken": r'\b(broke|broken|damaged|cracked|not working)\b',
            "help": r'\b(help|assist|support)\b'
        }
        
        is_ambiguous = False
        for pattern_type, pattern in ambiguous_patterns.items():
            if re.search(pattern, lower_msg):
                is_ambiguous = True
                break
        
        # Strategy 1: If NO appliance type detected, ask for it
        if is_ambiguous and not entities.get("appliance_type") and not context.get("appliance"):
            print(f"🔍 Detected ambiguous prompt without appliance type: {message[:50]}")
            return ChatResponse(
                assistant_text="I can help with that! To find the right part, is this for a refrigerator or dishwasher?",
                cards=[],
                quick_replies=[
                    "🧊 Refrigerator",
                    "🍽️ Dishwasher",
                    "I have a part number"
                ]
            )
        
        # Strategy 2: If appliance detected but vague part/symptom
        appliance_type = entities.get("appliance_type") or context.get("appliance")
        
        if is_ambiguous and appliance_type:
            part_component = entities.get("part_component")
            symptom = entities.get("symptom")
            
            if part_component:
                # User mentioned a component (e.g., "shelf", "drawer")
                print(f"🔍 Detected component '{part_component}' for {appliance_type}")
                return ChatResponse(
                    assistant_text=(
                        f"I'll help you find {part_component} parts for your {appliance_type}. "
                        f"Do you have your model number? (Found on a label inside the door)"
                    ),
                    cards=[],
                    quick_replies=[
                        f"Search {part_component} parts",
                        "I have my model number",
                        "Where's my model number?"
                    ]
                )
            elif symptom:
                # User described a problem - route to troubleshooting
                print(f"🔍 Detected symptom in ambiguous prompt: {symptom}")
                return await self._handle_troubleshoot(message, entities, context)
            else:
                # Truly vague - ask what they need
                return ChatResponse(
                    assistant_text=f"I can help with your {appliance_type}! What specifically are you looking for?",
                    cards=[],
                    quick_replies=[
                        "Find a specific part",
                        "Troubleshoot a problem",
                        "Check compatibility"
                    ]
                )
        
        # Standard handling for explicit reset or fresh start
        is_explicit_reset = any(phrase in lower_msg for phrase in [
            "start over", "main menu", "what can you do", "hello", "hi"
        ])
        
        if is_explicit_reset or not context:
            return ChatResponse(
                assistant_text="I can help you find refrigerator and dishwasher parts, check compatibility, troubleshoot issues, or assist with orders. What do you need help with?",
                quick_replies=[
                    "Find a part",
                    "Check compatibility",
                    "Troubleshoot an issue",
                    "Order support"
                ]
            )
        else:
            # User said something unclear - clarify based on context
            if appliance_type:
                return ChatResponse(
                    assistant_text=f"I'm here to help with your {appliance_type}. What would you like to do?",
                    quick_replies=[
                        "Find a part",
                        "Troubleshoot an issue",
                        "Check compatibility"
                    ]
                )
            else:
                return ChatResponse(
                    assistant_text="I didn't quite understand that. I can help you find parts, troubleshoot issues, or check compatibility for refrigerators and dishwashers.",
                    quick_replies=[
                        "Find a part",
                        "Troubleshoot an issue"
                    ]
                )
    
    async def _handle_cart_operation(
        self, 
        operation: str, 
        message: str, 
        entities: Dict, 
        context: Dict
    ) -> ChatResponse:
        """
        Handle multi-step cart operations: update quantity, remove, checkout, view.
        Supports conversational flows like "make that two" or "remove that part".
        """
        from database import get_db
        
        db = get_db()
        cart_id = context.get("cartId")
        
        if not cart_id:
            return ChatResponse(
                assistant_text="Your cart is empty. Would you like to find some parts?",
                cards=[],
                quick_replies=["Find parts", "Troubleshoot issue"]
            )
        
        # Operation: Update quantity
        if operation == "cart_update":
            # Extract new quantity
            match = re.search(r'(\d+)', message)
            if not match:
                return ChatResponse(
                    assistant_text="How many would you like? Please specify a quantity.",
                    cards=[],
                    quick_replies=["1", "2", "3", "View cart"]
                )
            
            new_qty = int(match.group(1))
            
            # Get last added item from context
            last_part = context.get("lastAddedPart")
            if not last_part:
                # Try to get the most recent cart item
                cart_items = db.table("cart_items").select("partselect_number").eq(
                    "cart_id", cart_id
                ).order("created_at", desc=True).limit(1).execute()
                
                if cart_items.data:
                    last_part = cart_items.data[0]["partselect_number"]
                else:
                    return ChatResponse(
                        assistant_text="Which item would you like to update?",
                        cards=[],
                        quick_replies=["View cart"]
                    )
            
            # Update quantity
            try:
                db.table("cart_items").update({
                    "quantity": new_qty
                }).eq("cart_id", cart_id).eq("partselect_number", last_part).execute()
                
                return ChatResponse(
                    assistant_text=f"✅ Updated {last_part} quantity to {new_qty}.",
                    cards=[],
                    quick_replies=["View cart", "Checkout", "Find more parts"]
                )
            except Exception as e:
                print(f"⚠️  Cart update failed: {e}")
                return ChatResponse(
                    assistant_text="Sorry, I couldn't update your cart. Please try again.",
                    cards=[],
                    quick_replies=["View cart"]
                )
        
        # Operation: Remove item
        elif operation == "cart_remove":
            # Try to get part number from message or context
            part_number = entities.get("part_number") or context.get("lastAddedPart")
            
            if not part_number:
                # Show current cart and ask which to remove
                cart_items = db.table("cart_items").select("partselect_number, parts(name)").eq(
                    "cart_id", cart_id
                ).execute()
                
                if not cart_items.data:
                    return ChatResponse(
                        assistant_text="Your cart is empty.",
                        cards=[],
                        quick_replies=["Find parts"]
                    )
                
                part_names = [f"{item['partselect_number']} ({item['parts']['name']})" for item in cart_items.data]
                
                return ChatResponse(
                    assistant_text="Which item would you like to remove?",
                    cards=[],
                    quick_replies=part_names[:3] + ["View full cart"]
                )
            
            # Remove the item
            try:
                db.table("cart_items").delete().eq(
                    "cart_id", cart_id
                ).eq("partselect_number", part_number).execute()
                
                return ChatResponse(
                    assistant_text=f"✅ Removed {part_number} from your cart.",
                    cards=[],
                    quick_replies=["View cart", "Find more parts"]
                )
            except Exception as e:
                print(f"⚠️  Cart removal failed: {e}")
                return ChatResponse(
                    assistant_text="Sorry, I couldn't remove that item. Please try again.",
                    cards=[],
                    quick_replies=["View cart"]
                )
        
        # Operation: View cart
        elif operation == "cart_view":
            try:
                cart = db.table("cart_items").select("*, parts(*)").eq("cart_id", cart_id).execute()
                
                if not cart.data:
                    return ChatResponse(
                        assistant_text="Your cart is empty.",
                        cards=[],
                        quick_replies=["Find parts", "Troubleshoot issue"]
                    )
                
                # Build cart summary
                items_text = []
                total_cents = 0
                for item in cart.data:
                    part_name = item["parts"]["name"]
                    qty = item.get("quantity", 1)
                    price = item["parts"].get("price_cents")
                    
                    if price:
                        total_cents += price * qty
                        items_text.append(f"• {part_name} (x{qty}) - ${(price * qty) / 100:.2f}")
                    else:
                        items_text.append(f"• {part_name} (x{qty}) - Price unavailable")
                
                return ChatResponse(
                    assistant_text=(
                        f"🛒 **Your Cart** ({len(cart.data)} {'item' if len(cart.data) == 1 else 'items'}):\n\n"
                        f"{chr(10).join(items_text)}\n\n"
                        f"**Subtotal: ${total_cents / 100:.2f}**"
                    ),
                    cards=[],
                    quick_replies=["Checkout", "Find more parts", "Remove an item"]
                )
            except Exception as e:
                print(f"⚠️  Cart view failed: {e}")
                return ChatResponse(
                    assistant_text="Sorry, I couldn't load your cart. Please try again.",
                    cards=[],
                    quick_replies=["Try again"]
                )
        
        # Operation: Checkout
        elif operation == "cart_checkout":
            try:
                cart = db.table("cart_items").select("*, parts(*)").eq("cart_id", cart_id).execute()
                
                if not cart.data:
                    return ChatResponse(
                        assistant_text="Your cart is empty. Add some parts first!",
                        cards=[],
                        quick_replies=["Find parts"]
                    )
                
                total_cents = sum(
                    (item["parts"].get("price_cents") or 0) * item.get("quantity", 1)
                    for item in cart.data
                )
                
                # Build PartSelect cart URL (if possible)
                part_numbers = [item["partselect_number"] for item in cart.data]
                partselect_url = "https://www.partselect.com/cart"  # Generic cart URL
                
                return ChatResponse(
                    assistant_text=(
                        f"🛒 **Ready to Checkout**\n\n"
                        f"**{len(cart.data)} {'item' if len(cart.data) == 1 else 'items'}** • **Total: ${total_cents / 100:.2f}**\n\n"
                        f"To complete your order, visit PartSelect.com. I can help you with installation guides or compatibility checks first!"
                    ),
                    cards=[{
                        "type": "checkout",
                        "id": "checkout_ready",
                        "data": {
                            "items": len(cart.data),
                            "total": total_cents / 100,
                            "checkoutUrl": partselect_url
                        }
                    }],
                    quick_replies=[
                        "View installation help",
                        "Check compatibility",
                        "Continue shopping"
                    ]
                )
            except Exception as e:
                print(f"⚠️  Checkout failed: {e}")
                return ChatResponse(
                    assistant_text="Sorry, I couldn't prepare your checkout. Please try again.",
                    cards=[],
                    quick_replies=["View cart"]
                )
        
        # Unknown operation
        return ChatResponse(
            assistant_text="I'm not sure what you want to do with your cart. You can view it, update quantities, or checkout.",
            cards=[],
            quick_replies=["View cart", "Checkout"]
        )
    
    def _create_product_card(self, part: Dict) -> Dict:
        """
        Create a product card from part data.
        GUARDRAIL: Add provenance labels for price/stock data.
        """
        price_cents = part.get("price_cents")
        stock_status = part.get("stock_status")
        in_stock = True if stock_status == "in_stock" else False if stock_status == "out_of_stock" else None
        updated_at = part.get("updated_at")
        
        # GUARDRAIL: Provenance labels for price/stock
        provenance = None
        if price_cents is not None or stock_status not in [None, "unknown"]:
            if updated_at:
                # Data from database with timestamp
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    provenance = f"As of {dt.strftime('%Y-%m-%d')}"
                except:
                    provenance = "From seed catalog"
            else:
                provenance = "From seed catalog"

        return {
            "type": "product",
            "id": f"product_{part['partselect_number']}",
            "data": {
                "title": part["name"],
                "price": (price_cents / 100) if isinstance(price_cents, (int, float)) else None,
                "currency": "USD",
                "inStock": in_stock,
                "partselectNumber": part["partselect_number"],
                "manufacturerPartNumber": part.get("manufacturer_number"),
                "rating": part.get("rating"),
                "reviewCount": part.get("review_count", 0),
                "imageUrl": part.get("image_url"),
                "productUrl": part.get("canonical_url") or part.get("product_url"),
                "provenance": provenance,  # NEW: Shows data source/timestamp
                "install": {
                    "hasInstructions": part.get("has_install_instructions", False),
                    "hasVideos": part.get("has_videos", False),
                    "links": part.get("install_links", [])
                },
                "cta": {
                    "action": "add_to_cart",
                    "payload": {"sku": part["partselect_number"]}
                }
            }
        }
