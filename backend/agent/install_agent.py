"""Installation sub-agent.

Handles:
- installation help flows
- dynamic scraping of instructions
- price enrichment for install requests
"""

from typing import Dict, Any, Optional

from models import ChatResponse


async def handle_install_help(
    orchestrator: "AgentOrchestrator",
    message: str,
    entities: Dict[str, Any],
    session_id: Optional[str] = None,
) -> ChatResponse:
    """Logic extracted from AgentOrchestrator._handle_install_help."""
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
                historical_entities = orchestrator._extract_entities(content)
                if historical_entities.get("part_number"):
                    part_number = historical_entities["part_number"]
                    print(f"   Found part number in history: {part_number}")
                    break

    # GUARDRAIL: Must have part number
    if not part_number:
        return ChatResponse(
            assistant_text=(
                "Which part do you need installation help with? "
                "Please provide the PartSelect number (PS####) or product link."
            ),
            cards=[],
            quick_replies=["Example: PS11701542", "Share product link"],
        )

    result = db.table("parts").select("*").eq("partselect_number", part_number).execute()

    if not result.data:
        return ChatResponse(
            assistant_text=f"I couldn't find part {part_number}.",
            cards=[],
        )

    part = result.data[0]
    part_name = part["name"].lower()
    product_url = part.get("canonical_url") or part.get("product_url")

    # GUARDRAIL: Product-specific installation guidance
    # Try dynamic scraping first if we have a URL
    install_instructions: Optional[str] = None

    if product_url:
        print(f"\n🔧 Attempting to scrape installation instructions from {product_url}")
        try:
            from services.install_scraper import extract_install_instructions

            install_instructions = await extract_install_instructions(
                url=product_url, part_name=part["name"], part_number=part_number
            )
        except Exception as e:  # pragma: no cover - network / scraping
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
                        db.table("parts").update(
                            {
                                "price_cents": price_cents,
                                "stock_status": availability,
                            }
                        ).eq("partselect_number", part_number).execute()
                except Exception as e:  # pragma: no cover - scraping issues
                    print(f"⚠️  Price fetch failed: {e}")

        # Create product card for context
        product_card = orchestrator._create_product_card(part)

        return ChatResponse(
            assistant_text=f"Here's how to install **{part['name']}**:\n\n{install_instructions}",
            cards=[product_card],  # Include product card with instructions
            quick_replies=["View full instructions on PartSelect", "Add to cart", "Check compatibility"],
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
                        db.table("parts").update(
                            {
                                "price_cents": price_cents,
                                "stock_status": availability,
                            }
                        ).eq("partselect_number", part_number).execute()
                except Exception as e:  # pragma: no cover
                    print(f"⚠️  Price fetch failed: {e}")

        # We have product-specific instructions from seed data
        product_card = orchestrator._create_product_card(part)

        return ChatResponse(
            assistant_text=f"Here's how to install {part['name']}:\n\n{install_summary}",
            cards=[product_card],  # Include product card with instructions
            quick_replies=["View full instructions on PartSelect", "Add to cart", "Check compatibility"],
        )

    # GUARDRAIL: If no product-specific instructions, link out instead of inventing steps
    # Detect simple parts that don't need power disconnection
    simple_parts = [
        "shelf",
        "bin",
        "drawer",
        "rack",
        "knob",
        "handle",
        "cover",
        "cap",
        "trim",
    ]
    is_simple_part = any(keyword in part_name for keyword in simple_parts)

    if is_simple_part:
        return ChatResponse(
            assistant_text=(
                f"**{part['name']}** is typically a simple snap-in or tool-free installation. "
                f"For product-specific instructions, diagrams, and videos, please visit the PartSelect product page."
            ),
            cards=[
                {
                    "type": "out_of_scope",
                    "id": "install_link_out",
                    "data": {
                        "message": f"Installation instructions for {part_number}",
                        "suggestedActions": [
                            "View instructions on PartSelect",
                            "Watch installation videos",
                            "Check compatibility",
                        ],
                    },
                }
            ],
            quick_replies=[
                "View on PartSelect" if product_url else None,
                "Add to cart",
                "Check compatibility",
            ],
        )

    # For electrical/mechanical parts, link out for safety
    return ChatResponse(
        assistant_text=(
            f"**{part['name']}** installation requires careful attention to safety and proper procedures. "
            f"For detailed product-specific instructions, safety warnings, diagrams, and videos, "
            f"please visit the PartSelect product page."
        ),
        cards=[
            {
                "type": "out_of_scope",
                "id": "install_link_out",
                "data": {
                    "message": f"Installation instructions for {part_number}",
                    "suggestedActions": [
                        "View instructions on PartSelect",
                        "Watch installation videos",
                        "Check compatibility",
                    ],
                },
            }
        ],
        quick_replies=[
            "View on PartSelect" if product_url else None,
            "Add to cart",
            "Check compatibility",
        ],
    )

