"""
Etsy Listing Creator
Uses Claude to write SEO-optimized listing content, then posts via the Etsy API.

Usage:
  python listings/listing_creator.py --product "boho wall art printable" \
      --type digital --price 4.99 --dry-run

  Remove --dry-run to actually post to Etsy (requires ETSY_* env vars).

Claude generates:
  - Title (≤140 chars, keyword-front-loaded)
  - Description (400-600 words, Etsy SEO best practices)
  - 13 tags (single words or short phrases, no duplicates)
  - Suggested taxonomy ID
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic

# Etsy taxonomy IDs for common categories
TAXONOMY_IDS = {
    "digital_prints": 2078,
    "digital_other": 2079,
    "wall_art": 1,
    "clothing": 69,
    "home_decor": 68,
    "stationery": 522,
    "craft_supplies": 75,
    "jewelry": 165,
    "wedding": 1,
    "default": 2078,
}

LISTING_SYSTEM_PROMPT = """You are an expert Etsy SEO copywriter with 10+ years experience.
Your listings consistently rank on the first page of Etsy search.

Rules you always follow:
- Title: exactly 1 sentence, ≤140 chars, most important keyword first
- Description: 400-600 words, weave in 5-7 keywords naturally, include what buyers get,
  how to use it, file formats (if digital), and a brief call-to-action at the end
- Tags: exactly 13 tags, mix of long-tail phrases and single keywords,
  no tag repeats title words already covered
- Respond ONLY with valid JSON (no markdown fences)
"""

LISTING_USER_PROMPT = """Create an Etsy listing for: {product}
Product type: {product_type}
Target price: ${price}
Additional context: {context}

Return JSON with this exact shape:
{{
  "title": "...",
  "description": "...",
  "tags": ["tag1", "tag2", ...13 total],
  "taxonomy_id": <integer from the list: digital_prints=2078, wall_art=1, stationery=522, clothing=69, home_decor=68>,
  "seo_notes": "Brief explanation of keyword strategy used"
}}"""


def generate_listing_content(
    product: str,
    product_type: str = "digital",
    price: float = 4.99,
    context: str = "",
) -> dict:
    """Call Claude to generate optimized listing content."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=LISTING_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": LISTING_USER_PROMPT.format(
                    product=product,
                    product_type=product_type,
                    price=price,
                    context=context or "none",
                ),
            }
        ],
    )

    raw = message.content[0].text.strip()
    # Strip accidental markdown fences if Claude adds them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def create_listing(
    product: str,
    product_type: str = "digital",
    price: float = 4.99,
    quantity: int = 999,
    context: str = "",
    dry_run: bool = True,
) -> dict:
    """Generate content and (optionally) post to Etsy."""
    print(f"[listing_creator] Generating content for: {product}")
    content = generate_listing_content(product, product_type, price, context)

    result = {
        "product": product,
        "generated_content": content,
        "etsy_listing_id": None,
        "etsy_listing_url": None,
        "dry_run": dry_run,
    }

    if not dry_run:
        from api.etsy_client import EtsyClient
        client = EtsyClient()
        listing_type = "download" if product_type == "digital" else "physical"
        response = client.create_listing(
            title=content["title"],
            description=content["description"],
            price_usd=price,
            quantity=quantity,
            tags=content["tags"],
            taxonomy_id=content.get("taxonomy_id", TAXONOMY_IDS["default"]),
            listing_type=listing_type,
        )
        listing_id = response.get("listing_id")
        result["etsy_listing_id"] = listing_id
        result["etsy_listing_url"] = f"https://www.etsy.com/listing/{listing_id}"
        print(f"[listing_creator] Created listing: {result['etsy_listing_url']}")
    else:
        print("[listing_creator] DRY RUN — listing NOT posted to Etsy")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create an Etsy listing")
    parser.add_argument("--product", required=True, help="Product name/description")
    parser.add_argument("--type", default="digital", choices=["digital", "pod", "handmade"])
    parser.add_argument("--price", type=float, default=4.99)
    parser.add_argument("--context", default="", help="Extra context for Claude")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--live", action="store_true", help="Actually post to Etsy")
    args = parser.parse_args()

    result = create_listing(
        product=args.product,
        product_type=args.type,
        price=args.price,
        context=args.context,
        dry_run=not args.live,
    )
    print(json.dumps(result, indent=2))
