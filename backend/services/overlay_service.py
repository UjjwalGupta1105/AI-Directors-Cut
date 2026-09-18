import os
import logging
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    font_candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    if bold:
        font_candidates = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
        ] + font_candidates

    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def create_intro_overlay(
    width: int,
    height: int,
    title: str,
    output_png: str,
    subtitle: str = ""
) -> str:
    """Generate a sleek broadcast-style lower-third intro card focused on the video."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = min(width / 1920.0, height / 1080.0)
    scale = max(0.6, min(scale, 1.4))

    card_w = int(min(width * 0.75, 750 * scale))
    card_h = int(140 * scale)
    x0 = int(50 * scale)
    y0 = height - card_h - int(60 * scale)
    x1 = x0 + card_w
    y1 = y0 + card_h

    # Card background (dark translucent glass)
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=int(18 * scale),
        fill=(13, 13, 24, 220),
        outline=(139, 92, 246, 140),
        width=max(1, int(2 * scale))
    )

    # Accent left border glow
    draw.rounded_rectangle(
        [x0, y0, x0 + int(6 * scale), y1],
        radius=int(3 * scale),
        fill=(168, 85, 247, 240)
    )

    # Pill badge: "✦ FEATURED HIGHLIGHTS"
    pill_w = int(195 * scale)
    pill_h = int(28 * scale)
    px0 = x0 + int(24 * scale)
    py0 = y0 + int(18 * scale)
    draw.rounded_rectangle(
        [px0, py0, px0 + pill_w, py0 + pill_h],
        radius=int(14 * scale),
        fill=(139, 92, 246, 45),
        outline=(168, 85, 247, 180),
        width=1
    )
    badge_font = _get_font(int(13 * scale), bold=True)
    draw.text((px0 + int(12 * scale), py0 + int(5 * scale)), "✦ FEATURED HIGHLIGHTS", fill=(216, 180, 254, 255), font=badge_font)

    # Title text
    title_font = _get_font(int(24 * scale), bold=True)
    clean_title = title if len(title) <= 45 else title[:42] + "..."
    draw.text((x0 + int(24 * scale), y0 + int(54 * scale)), clean_title, fill=(255, 255, 255, 250), font=title_font)

    # Subtitle text
    sub_font = _get_font(int(14 * scale))
    if subtitle:
        clean_sub = subtitle if len(subtitle) <= 65 else subtitle[:62] + "..."
    else:
        clean_sub = "Key Moments & Essential Insights • Complete Breakdown"
    draw.text((x0 + int(24 * scale), y0 + int(96 * scale)), clean_sub, fill=(200, 200, 225, 180), font=sub_font)

    img.save(output_png, "PNG")
    logger.info(f"Generated intro overlay: {output_png}")
    return output_png


def create_moment_overlay(
    width: int,
    height: int,
    moment_idx: int,
    total_moments: int,
    score: int,
    moment_title: str,
    reason: str,
    output_png: str
) -> str:
    """Generate sleek moment badges: top-left chapter tag and bottom-left reason banner."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = min(width / 1920.0, height / 1080.0)
    scale = max(0.6, min(scale, 1.4))

    # 1. Top-left Chapter pill
    top_w = int(280 * scale)
    top_h = int(46 * scale)
    tx0 = int(50 * scale)
    ty0 = int(50 * scale)
    draw.rounded_rectangle(
        [tx0, ty0, tx0 + top_w, ty0 + top_h],
        radius=int(14 * scale),
        fill=(13, 13, 24, 215),
        outline=(139, 92, 246, 150),
        width=max(1, int(1.5 * scale))
    )
    # Highlight pill indicator
    draw.rounded_rectangle(
        [tx0 + int(8 * scale), ty0 + int(8 * scale), tx0 + int(36 * scale), ty0 + top_h - int(8 * scale)],
        radius=int(6 * scale),
        fill=(168, 85, 247, 240)
    )
    chap_num_font = _get_font(int(14 * scale), bold=True)
    draw.text(
        (tx0 + int(14 * scale), ty0 + int(12 * scale)),
        f"{moment_idx:02d}",
        fill=(255, 255, 255, 255),
        font=chap_num_font
    )

    chap_font = _get_font(int(14 * scale), bold=True)
    score_stars = "★" * min(score, 5)
    draw.text(
        (tx0 + int(44 * scale), ty0 + int(12 * scale)),
        f"MOMENT {moment_idx}/{total_moments} • SCORE {score}/10",
        fill=(235, 235, 250, 240),
        font=chap_font
    )

    # 2. Bottom-left Moment Context Card
    card_w = int(min(width * 0.72, 700 * scale))
    card_h = int(105 * scale)
    bx0 = int(50 * scale)
    by0 = height - card_h - int(60 * scale)
    bx1 = bx0 + card_w
    by1 = by0 + card_h

    draw.rounded_rectangle(
        [bx0, by0, bx1, by1],
        radius=int(16 * scale),
        fill=(13, 13, 24, 210),
        outline=(99, 102, 241, 130),
        width=max(1, int(1.5 * scale))
    )

    # Left accent bar
    draw.rounded_rectangle(
        [bx0, by0, bx0 + int(5 * scale), by1],
        radius=int(3 * scale),
        fill=(129, 140, 248, 230)
    )

    # Header title
    title_font = _get_font(int(18 * scale), bold=True)
    clean_t = moment_title if moment_title else f"Highlight Moment {moment_idx}"
    if len(clean_t) > 42:
        clean_t = clean_t[:39] + "..."
    draw.text(
        (bx0 + int(22 * scale), by0 + int(16 * scale)),
        f"✦ {clean_t}",
        fill=(255, 255, 255, 250),
        font=title_font
    )

    # Reason / Description
    desc_font = _get_font(int(13 * scale))
    clean_r = reason if len(reason) <= 75 else reason[:72] + "..."
    draw.text(
        (bx0 + int(22 * scale), by0 + int(52 * scale)),
        clean_r,
        fill=(205, 210, 230, 195),
        font=desc_font
    )

    img.save(output_png, "PNG")
    logger.info(f"Generated moment overlay: {output_png}")
    return output_png


def create_outro_overlay(
    width: int,
    height: int,
    title: str,
    output_png: str,
    subtitle: str = ""
) -> str:
    """Generate a clean concluding lower-third card focused on the video."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = min(width / 1920.0, height / 1080.0)
    scale = max(0.6, min(scale, 1.4))

    card_w = int(min(width * 0.75, 680 * scale))
    card_h = int(120 * scale)
    x0 = int(50 * scale)
    y0 = height - card_h - int(60 * scale)
    x1 = x0 + card_w
    y1 = y0 + card_h

    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=int(18 * scale),
        fill=(13, 13, 24, 225),
        outline=(236, 72, 153, 140),
        width=max(1, int(2 * scale))
    )

    # Left pink-violet accent
    draw.rounded_rectangle(
        [x0, y0, x0 + int(6 * scale), y1],
        radius=int(3 * scale),
        fill=(236, 72, 153, 240)
    )

    # Badge
    pill_w = int(195 * scale)
    pill_h = int(28 * scale)
    px0 = x0 + int(22 * scale)
    py0 = y0 + int(18 * scale)
    draw.rounded_rectangle(
        [px0, py0, px0 + pill_w, py0 + pill_h],
        radius=int(14 * scale),
        fill=(236, 72, 153, 40),
        outline=(244, 114, 182, 180),
        width=1
    )
    badge_font = _get_font(int(13 * scale), bold=True)
    draw.text((px0 + int(12 * scale), py0 + int(5 * scale)), "✦ SUMMARY & WRAP-UP", fill=(249, 168, 212, 255), font=badge_font)

    # Outro title text
    title_font = _get_font(int(20 * scale), bold=True)
    clean_title = title if len(title) <= 45 else title[:42] + "..."
    draw.text((x0 + int(22 * scale), y0 + int(56 * scale)), clean_title, fill=(255, 255, 255, 250), font=title_font)

    # Subtitle
    sub_font = _get_font(int(13 * scale))
    if subtitle:
        clean_sub = subtitle if len(subtitle) <= 65 else subtitle[:62] + "..."
    else:
        clean_sub = "Key Takeaways & Core Insights • Thank you for watching!"
    draw.text((x0 + int(22 * scale), y0 + int(86 * scale)), clean_sub, fill=(210, 210, 230, 180), font=sub_font)

    img.save(output_png, "PNG")
    logger.info(f"Generated outro overlay: {output_png}")
    return output_png
