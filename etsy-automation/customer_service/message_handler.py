"""
Etsy Customer Service Handler
Fetches open buyer messages and uses Claude to draft (or auto-send) replies.

Usage:
  python customer_service/message_handler.py --list          # show open messages
  python customer_service/message_handler.py --draft-all     # draft replies, print only
  python customer_service/message_handler.py --send-all      # draft + send replies
  python customer_service/message_handler.py --id <conv_id>  # handle one conversation
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic

SYSTEM_PROMPT = """You are a friendly, professional Etsy seller's customer service assistant.
Your replies are:
- Warm but concise (3-5 sentences max)
- Helpful and solution-focused
- Written in a conversational tone that feels human, not robotic
- Free of filler phrases ("Of course!", "Certainly!", "Absolutely!")

If the buyer has a problem, acknowledge it and offer a concrete fix.
If they have a question, answer it directly.
If it's a review/thank-you, reply briefly and invite them back.

Respond with ONLY the reply message text — no subject line, no JSON wrapper."""


def _claude_draft(conversation_snippet: str, shop_context: str = "") -> str:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",   # Fast and cheap for CS replies
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Shop context: {shop_context or 'Small Etsy shop selling digital downloads.'}\n\n"
                    f"Buyer message:\n{conversation_snippet}\n\n"
                    "Draft a reply."
                ),
            }
        ],
    )
    return message.content[0].text.strip()


def list_conversations(client) -> list:
    convs = client.get_conversations(limit=50)
    # Filter to conversations with unread messages
    unread = [c for c in convs if c.get("unread_count", 0) > 0]
    return unread


def draft_reply(conv: dict, shop_context: str = "") -> dict:
    messages = conv.get("messages", [])
    latest = messages[-1].get("message_body", "") if messages else ""
    reply = _claude_draft(latest, shop_context)
    return {
        "conversation_id": conv.get("conversation_id"),
        "buyer_name": conv.get("buyer_user_id"),
        "latest_message": latest[:200],
        "draft_reply": reply,
    }


def handle_conversations(
    mode: str = "draft",    # "draft" | "send"
    conversation_id: int = 0,
    shop_context: str = "",
) -> list:
    from api.etsy_client import EtsyClient
    client = EtsyClient()

    if conversation_id:
        # Handle a single conversation
        convs = [{"conversation_id": conversation_id, "messages": [], "unread_count": 1}]
        all_convs = client.get_conversations(limit=100)
        for c in all_convs:
            if c.get("conversation_id") == conversation_id:
                convs = [c]
                break
    else:
        convs = list_conversations(client)

    results = []
    for conv in convs:
        draft = draft_reply(conv, shop_context)
        results.append(draft)

        if mode == "send":
            client.send_message(draft["conversation_id"], draft["draft_reply"])
            draft["sent"] = True
            print(f"[cs] Sent reply to conversation {draft['conversation_id']}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--draft-all", action="store_true")
    parser.add_argument("--send-all", action="store_true")
    parser.add_argument("--id", type=int, default=0)
    parser.add_argument("--shop-context", default="", help="Brief description of your shop")
    args = parser.parse_args()

    if args.list:
        from api.etsy_client import EtsyClient
        convs = list_conversations(EtsyClient())
        print(f"[cs] {len(convs)} unread conversation(s)")
        for c in convs:
            msgs = c.get("messages", [])
            latest = msgs[-1].get("message_body", "")[:100] if msgs else ""
            print(f"  #{c.get('conversation_id')} — {latest!r}")
    elif args.send_all:
        results = handle_conversations("send", shop_context=args.shop_context)
        print(json.dumps(results, indent=2))
    elif args.draft_all or args.id:
        results = handle_conversations(
            "draft", conversation_id=args.id, shop_context=args.shop_context
        )
        print(json.dumps(results, indent=2))
    else:
        parser.print_help()
