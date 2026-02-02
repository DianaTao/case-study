"""Commerce sub-agent.

Handles:
- cart operations (update quantity, remove, view, checkout)
- returns policy responses
"""

from typing import Dict, Any

from models import ChatResponse


async def handle_cart_operation(
    orchestrator: "AgentOrchestrator",
    operation: str,
    message: str,
    entities: Dict[str, Any],
    context: Dict[str, Any],
) -> ChatResponse:
    """Logic extracted from AgentOrchestrator._handle_cart_operation."""
    from database import get_db

    db = get_db()
    cart_id = context.get("cartId")

    if not cart_id:
        return ChatResponse(
            assistant_text="Your cart is empty. Would you like to find some parts?",
            cards=[],
            quick_replies=["Find parts", "Troubleshoot issue"],
        )

    # Operation: Update quantity
    if operation == "cart_update":
        # Extract new quantity
        import re

        match = re.search(r"(\d+)", message)
        if not match:
            return ChatResponse(
                assistant_text="How many would you like? Please specify a quantity.",
                cards=[],
                quick_replies=["1", "2", "3", "View cart"],
            )

        new_qty = int(match.group(1))

        # Get last added item from context
        last_part = context.get("lastAddedPart")
        if not last_part:
            # Try to get the most recent cart item
            cart_items = (
                db.table("cart_items")
                .select("partselect_number")
                .eq("cart_id", cart_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if cart_items.data:
                last_part = cart_items.data[0]["partselect_number"]
            else:
                return ChatResponse(
                    assistant_text="Which item would you like to update?",
                    cards=[],
                    quick_replies=["View cart"],
                )

        # Update quantity
        try:
            db.table("cart_items").update({"quantity": new_qty}).eq("cart_id", cart_id).eq(
                "partselect_number", last_part
            ).execute()

            return ChatResponse(
                assistant_text=f"✅ Updated {last_part} quantity to {new_qty}.",
                cards=[],
                quick_replies=["View cart", "Checkout", "Find more parts"],
            )
        except Exception as e:  # pragma: no cover - DB failure
            print(f"⚠️  Cart update failed: {e}")
            return ChatResponse(
                assistant_text="Sorry, I couldn't update your cart. Please try again.",
                cards=[],
                quick_replies=["View cart"],
            )

    # Operation: Remove item
    elif operation == "cart_remove":
        # Try to get part number from message or context
        part_number = entities.get("part_number") or context.get("lastAddedPart")

        if not part_number:
            # Show current cart and ask which to remove
            cart_items = (
                db.table("cart_items")
                .select("partselect_number, parts(name)")
                .eq("cart_id", cart_id)
                .execute()
            )

            if not cart_items.data:
                return ChatResponse(
                    assistant_text="Your cart is empty.",
                    cards=[],
                    quick_replies=["Find parts"],
                )

            part_names = [
                f"{item['partselect_number']} ({item['parts']['name']})"
                for item in cart_items.data
            ]

            return ChatResponse(
                assistant_text="Which item would you like to remove?",
                cards=[],
                quick_replies=part_names[:3] + ["View full cart"],
            )

        # Remove the item
        try:
            db.table("cart_items").delete().eq("cart_id", cart_id).eq(
                "partselect_number", part_number
            ).execute()

            return ChatResponse(
                assistant_text=f"✅ Removed {part_number} from your cart.",
                cards=[],
                quick_replies=["View cart", "Find more parts"],
            )
        except Exception as e:  # pragma: no cover
            print(f"⚠️  Cart removal failed: {e}")
            return ChatResponse(
                assistant_text="Sorry, I couldn't remove that item. Please try again.",
                cards=[],
                quick_replies=["View cart"],
            )

    # Operation: View cart
    elif operation == "cart_view":
        try:
            cart = db.table("cart_items").select("*, parts(*)").eq("cart_id", cart_id).execute()

            if not cart.data:
                return ChatResponse(
                    assistant_text="Your cart is empty.",
                    cards=[],
                    quick_replies=["Find parts", "Troubleshoot issue"],
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
                    items_text.append(
                        f"• {part_name} (x{qty}) - ${(price * qty) / 100:.2f}"
                    )
                else:
                    items_text.append(f"• {part_name} (x{qty}) - Price unavailable")

            return ChatResponse(
                assistant_text=(
                    f"🛒 **Your Cart** ({len(cart.data)} {'item' if len(cart.data) == 1 else 'items'}):\n\n"
                    f"{chr(10).join(items_text)}\n\n"
                    f"**Subtotal: ${total_cents / 100:.2f}**"
                ),
                cards=[],
                quick_replies=["Checkout", "Find more parts", "Remove an item"],
            )
        except Exception as e:  # pragma: no cover
            print(f"⚠️  Cart view failed: {e}")
            return ChatResponse(
                assistant_text="Sorry, I couldn't load your cart. Please try again.",
                cards=[],
                quick_replies=["Try again"],
            )

    # Operation: Checkout
    elif operation == "cart_checkout":
        try:
            cart = db.table("cart_items").select("*, parts(*)").eq("cart_id", cart_id).execute()

            if not cart.data:
                return ChatResponse(
                    assistant_text="Your cart is empty. Add some parts first!",
                    cards=[],
                    quick_replies=["Find parts"],
                )

            total_cents = sum(
                (item["parts"].get("price_cents") or 0) * item.get("quantity", 1)
                for item in cart.data
            )

            # Build PartSelect cart URL (if possible)
            partselect_url = "https://www.partselect.com/cart"  # Generic cart URL

            return ChatResponse(
                assistant_text=(
                    f"🛒 **Ready to Checkout**\n\n"
                    f"**{len(cart.data)} {'item' if len(cart.data) == 1 else 'items'}** • "
                    f"**Total: ${total_cents / 100:.2f}**\n\n"
                    f"To complete your order, visit PartSelect.com. I can help you with installation guides or compatibility checks first!"
                ),
                cards=[
                    {
                        "type": "checkout",
                        "id": "checkout_ready",
                        "data": {
                            "items": len(cart.data),
                            "total": total_cents / 100,
                            "checkoutUrl": partselect_url,
                        },
                    }
                ],
                quick_replies=[
                    "View installation help",
                    "Check compatibility",
                    "Continue shopping",
                ],
            )
        except Exception as e:  # pragma: no cover
            print(f"⚠️  Checkout failed: {e}")
            return ChatResponse(
                assistant_text="Sorry, I couldn't prepare your checkout. Please try again.",
                cards=[],
                quick_replies=["View cart"],
            )

    # Unknown operation
    return ChatResponse(
        assistant_text=(
            "I'm not sure what you want to do with your cart. "
            "You can view it, update quantities, or checkout."
        ),
        cards=[],
        quick_replies=["View cart", "Checkout"],
    )


async def handle_returns_policy() -> ChatResponse:
    """Logic extracted from AgentOrchestrator._handle_returns_policy."""
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
        quick_replies=["Start return", "Contact support"],
    )

