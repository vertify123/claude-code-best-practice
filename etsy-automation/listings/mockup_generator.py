"""
Etsy Listing Mockup Generator
Generates professional-looking product mockup images using Pillow.
No external APIs or services required.

Produces a 2000×2000 px image suitable for Etsy's primary listing thumbnail.

Usage:
  python listings/mockup_generator.py --title "Nurse Shift Planner" --type planner
  python listings/mockup_generator.py --title "Budget Tracker" --type spreadsheet --out /tmp/mockup.jpg
  python listings/mockup_generator.py --help

Supported --type values:
  planner, spreadsheet, checklist, template, tracker, printable, calendar
"""

import argparse
import os
import sys
import textwrap
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    sys.exit(
        "[mockup_generator] Pillow is required. Install with:\n"
        "  pip install Pillow"
    )

# ── Colour palettes per product type ─────────────────────────────────────────

PALETTES = {
    "planner":     {"bg1": (18, 32, 58),   "bg2": (38, 60, 100),  "accent": (0, 200, 255),  "badge": (0, 160, 220)},
    "spreadsheet": {"bg1": (15, 50, 35),   "bg2": (30, 90, 60),   "accent": (0, 230, 130),  "badge": (0, 180, 90)},
    "checklist":   {"bg1": (50, 20, 60),   "bg2": (90, 40, 110),  "accent": (200, 100, 255),"badge": (160, 60, 220)},
    "template":    {"bg1": (55, 30, 10),   "bg2": (100, 55, 15),  "accent": (255, 180, 50), "badge": (220, 140, 20)},
    "tracker":     {"bg1": (10, 35, 55),   "bg2": (25, 65, 95),   "accent": (80, 180, 255), "badge": (40, 140, 220)},
    "printable":   {"bg1": (50, 10, 30),   "bg2": (100, 20, 55),  "accent": (255, 80, 140), "badge": (220, 40, 100)},
    "calendar":    {"bg1": (30, 15, 50),   "bg2": (60, 28, 90),   "accent": (180, 130, 255),"badge": (140, 90, 230)},
}
DEFAULT_PALETTE = PALETTES["planner"]

SIZE = 2000  # Etsy recommends square 2000×2000 px


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _gradient_bg(draw: ImageDraw.ImageDraw, pal: dict) -> None:
    """Fill background with a vertical gradient."""
    r1, g1, b1 = pal["bg1"]
    r2, g2, b2 = pal["bg2"]
    for y in range(SIZE):
        t = y / SIZE
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        draw.line([(0, y), (SIZE, y)], fill=(r, g, b))


def _document_frame(img: Image.Image, draw: ImageDraw.ImageDraw, pal: dict) -> None:
    """Draw a white document card with a subtle shadow."""
    margin = 160
    card_x0, card_y0 = margin, margin + 80
    card_x1, card_y1 = SIZE - margin, SIZE - margin - 80

    # Shadow (slightly larger, darker)
    shadow_offset = 18
    shadow_color = (0, 0, 0, 60)
    shadow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    s_draw.rounded_rectangle(
        [card_x0 + shadow_offset, card_y0 + shadow_offset,
         card_x1 + shadow_offset, card_y1 + shadow_offset],
        radius=32, fill=shadow_color
    )
    shadow_blurred = shadow_layer.filter(ImageFilter.GaussianBlur(radius=24))
    img.paste(shadow_blurred, mask=shadow_blurred)

    # White card
    draw.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y1],
        radius=32, fill=(255, 255, 255, 242)
    )

    # Accent top bar
    draw.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y0 + 14],
        radius=8, fill=pal["accent"]
    )


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Best-effort font load — falls back to the built-in bitmap font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_lines(draw: ImageDraw.ImageDraw, pal: dict) -> None:
    """Draw decorative ruled lines on the document card."""
    line_color = (*pal["accent"][:3], 30)  # very faint
    margin = 160
    card_y0 = margin + 80 + 14
    card_y1 = SIZE - margin - 80
    content_top = card_y0 + 260
    content_bottom = card_y1 - 120
    line_gap = 55
    y = content_top
    while y < content_bottom:
        draw.line([(margin + 80, y), (SIZE - margin - 80, y)], fill=line_color, width=2)
        y += line_gap


def _draw_checkboxes(draw: ImageDraw.ImageDraw, pal: dict) -> None:
    """Draw small decorative checkboxes on the left margin."""
    margin = 160
    card_y0 = margin + 80 + 14
    content_top = card_y0 + 260
    card_y1 = SIZE - margin - 80
    content_bottom = card_y1 - 120
    box_x = margin + 82
    box_size = 28
    line_gap = 55
    states = [True, True, False, True, False, False, True, False, True, False,
              True, True, False, True, False, False, True, False, True, False]
    y = content_top
    i = 0
    while y < content_bottom - 20:
        bx, by = box_x, y - box_size // 2
        draw.rounded_rectangle([bx, by, bx + box_size, by + box_size], radius=5,
                                outline=pal["accent"], width=3)
        if states[i % len(states)]:
            draw.line([(bx + 6, by + 14), (bx + 12, by + 20)], fill=pal["accent"], width=4)
            draw.line([(bx + 12, by + 20), (bx + 22, by + 8)], fill=pal["accent"], width=4)
        y += line_gap
        i += 1


def _draw_title(draw: ImageDraw.ImageDraw, title: str, pal: dict) -> None:
    """Render the product title centred on the card."""
    margin = 160
    card_y0 = margin + 80 + 14
    card_x0, card_x1 = margin, SIZE - margin
    card_width = card_x1 - card_x0

    # Wrap title to ~20 chars per line
    lines = textwrap.wrap(title.upper(), width=20)

    font_size = 110 if len(lines) <= 2 else 90
    font = _load_font(font_size)

    total_h = len(lines) * (font_size + 16)
    start_y = card_y0 + 60

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = card_x0 + (card_width - text_w) // 2
        y = start_y + i * (font_size + 16)
        # Shadow
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 60))
        draw.text((x, y), line, font=font, fill=(30, 30, 40))


def _draw_subtitle(draw: ImageDraw.ImageDraw, subtitle: str, pal: dict) -> None:
    """Render a small subtitle below the title."""
    margin = 160
    card_x0, card_x1 = margin, SIZE - margin
    card_width = card_x1 - card_x0
    font = _load_font(48)

    bbox = draw.textbbox((0, 0), subtitle, font=font)
    text_w = bbox[2] - bbox[0]
    x = card_x0 + (card_width - text_w) // 2
    y = margin + 80 + 14 + 220
    draw.text((x, y), subtitle, font=font, fill=(*pal["accent"], 200))


def _draw_badge(draw: ImageDraw.ImageDraw, label: str, pal: dict) -> None:
    """Draw a 'Digital Download' badge at the bottom of the card."""
    margin = 160
    card_y1 = SIZE - margin - 80
    badge_h = 70
    badge_y0 = card_y1 - badge_h - 40
    badge_y1 = badge_y0 + badge_h

    font = _load_font(40)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    pad = 40
    badge_x0 = (SIZE - text_w - pad * 2) // 2
    badge_x1 = badge_x0 + text_w + pad * 2

    draw.rounded_rectangle([badge_x0, badge_y0, badge_x1, badge_y1],
                            radius=badge_h // 2, fill=pal["badge"])
    draw.text((badge_x0 + pad, badge_y0 + (badge_h - (bbox[3] - bbox[1])) // 2),
              label, font=font, fill=(255, 255, 255))


# ── Main generate function ────────────────────────────────────────────────────

def generate_mockup(
    title: str,
    product_type: str = "planner",
    subtitle: str = "Instant Digital Download",
    badge: str = "✦  DIGITAL DOWNLOAD  ✦",
    output_path: Optional[str] = None,
) -> str:
    """Generate a product mockup image and return the saved file path.

    Args:
        title: Product name shown prominently on the mockup.
        product_type: One of planner/spreadsheet/checklist/template/tracker/printable/calendar.
        subtitle: Small text under the top accent bar.
        badge: Text inside the bottom pill badge.
        output_path: Where to save the JPEG. Defaults to listings/mockups/<slug>.jpg.

    Returns:
        Absolute path to the saved image file.
    """
    pal = PALETTES.get(product_type, DEFAULT_PALETTE)

    # Determine output path
    if output_path is None:
        slug = title.lower().replace(" ", "-")[:50]
        out_dir = Path(__file__).parent / "mockups"
        out_dir.mkdir(exist_ok=True)
        output_path = str(out_dir / f"{slug}.jpg")

    # Create RGBA canvas
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    _gradient_bg(draw, pal)
    _document_frame(img, draw, pal)
    _draw_lines(draw, pal)
    _draw_checkboxes(draw, pal)
    _draw_title(draw, title, pal)
    _draw_subtitle(draw, subtitle, pal)
    _draw_badge(draw, badge, pal)

    # Convert to RGB and save as JPEG
    rgb = img.convert("RGB")
    rgb.save(output_path, "JPEG", quality=92, optimize=True)

    return output_path


# Need this at module level for the type hint inside the function
from typing import Optional


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        from dashboard.agent_logger import log_event as _log
    except ImportError:
        def _log(*_): pass

    parser = argparse.ArgumentParser(description="Generate a product mockup image for an Etsy listing")
    parser.add_argument("--title", required=True, help="Product title (shown on mockup)")
    parser.add_argument(
        "--type", dest="product_type", default="planner",
        choices=list(PALETTES.keys()),
        help="Product type (controls colour palette)",
    )
    parser.add_argument("--subtitle", default="Instant Digital Download")
    parser.add_argument("--badge", default="✦  DIGITAL DOWNLOAD  ✦")
    parser.add_argument("--out", dest="output_path", default=None,
                        help="Output JPEG path (default: listings/mockups/<slug>.jpg)")
    args = parser.parse_args()

    _log("etsy-image-agent", "start", f"Generating mockup for: {args.title}")
    saved = generate_mockup(
        title=args.title,
        product_type=args.product_type,
        subtitle=args.subtitle,
        badge=args.badge,
        output_path=args.output_path,
    )
    _log("etsy-image-agent", "complete", f"Mockup saved: {saved}")
    print(f"[mockup_generator] Saved: {saved}")
