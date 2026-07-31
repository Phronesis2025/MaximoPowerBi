#!/usr/bin/env python3
"""
build_backgrounds.py - generate Power BI page background images.

For every page in PAGES this writes, next to this script:
    <page>.svg   editable master, canvas in SVG user units, version-controlled
    <page>.png   raster export at png_scale x the canvas (2x = 2560x1440 for a
                 1280x720 page), for crispness on projectors

Design rules baked in:
  * No text inside any container - Power BI renders all of it. The only baked
    text is the header band title.
  * KPI cards carry a 3 px accent bar along their left edge, inset 1 px,
    clipped to the card's corner radius.

Rendering: cairosvg if it can load its native cairo library, else Pillow
draws the same PAGES data directly (no SVG rasterisation involved).

Run from anywhere:  python assets/backgrounds/build_backgrounds.py
"""

import os
import re
import sys

# ---------------------------------------------------------------------------
# Page definitions. Add a page = add a dict entry, not code.
# Rects are (x, y, w, h) in canvas user units.
# ---------------------------------------------------------------------------
PAGES = {
    "executive_overview": {
        "name": "Executive Overview",
        "canvas": (1920, 1080),
        "margin": 36,
        "png_scale": 2,
        "accent_w": 4,      # px, KPI accent bar width
        "accent_inset": 1,  # px, accent bar inset from the card edge
        "palette": {
            "page_bg": "#F4F5F7",
            "container_fill": "#FFFFFF",
            "container_border": "#E3E6EA",
            "container_radius": 8,
            "header_band": "#1B3A57",
            "divider": "#D9DEE4",   # reserved for pages that draw rule lines
            "kpi_accent": "#4477AA",
        },
        "header": {
            "rect": (0, 0, 1920, 108),
            "text": "Maximo Maintenance Analytics",
            "text_xy": (60, 66),          # x, baseline y
            "text_size": 33,
            "text_weight": 600,
            "text_color": "#FFFFFF",
            "font_stack": "Segoe UI, Arial, sans-serif",
        },
        # containers with the left-edge accent bar
        "kpi_cards": [
            (36, 126, 348, 156),
            (411, 126, 348, 156),
            (786, 126, 348, 156),
            (1161, 126, 348, 156),
            (1536, 126, 348, 156),
        ],
        # plain containers
        "panels": [
            (36, 300, 1140, 372),     # main chart panel
            (1212, 300, 672, 372),    # secondary chart panel
            (36, 690, 1848, 354),     # scorecard panel
        ],
    },
    "backlog_and_aging": {
        "name": "Backlog and Aging",
        "canvas": (1920, 1080),
        "margin": 36,
        "png_scale": 2,
        "accent_w": 4,
        "accent_inset": 1,
        "palette": {
            "page_bg": "#F4F5F7",
            "container_fill": "#FFFFFF",
            "container_border": "#E3E6EA",
            "container_radius": 8,
            "header_band": "#1B3A57",
            "divider": "#D9DEE4",
            "kpi_accent": "#4477AA",
        },
        "header": {
            "rect": (0, 0, 1920, 108),
            "text": "Maximo Maintenance Analytics",
            "text_xy": (60, 66),
            "text_size": 33,
            "text_weight": 600,
            "text_color": "#FFFFFF",
            "font_stack": "Segoe UI, Arial, sans-serif",
        },
        "kpi_cards": [
            (36, 126, 348, 156),
            (411, 126, 348, 156),
            (786, 126, 348, 156),
            (1161, 126, 348, 156),
            (1536, 126, 348, 156),
        ],
        "panels": [
            (36, 300, 1140, 372),
            (1212, 300, 672, 372),
            (36, 690, 1848, 354),
        ],
    },
}

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# SVG
# ---------------------------------------------------------------------------
def build_svg(page):
    W, H = page["canvas"]
    pal = page["palette"]
    r = pal["container_radius"]
    ACCENT_W, ACCENT_INSET = page["accent_w"], page["accent_inset"]
    hdr = page["header"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        f'  <rect x="0" y="0" width="{W}" height="{H}" fill="{pal["page_bg"]}"/>',
    ]

    def container(x, y, w, h):
        parts.append(
            f'  <rect x="{x + 0.5}" y="{y + 0.5}" width="{w - 1}" height="{h - 1}" '
            f'rx="{r}" fill="{pal["container_fill"]}" '
            f'stroke="{pal["container_border"]}" stroke-width="1"/>')

    for x, y, w, h in page["panels"]:
        container(x, y, w, h)

    parts.append('  <defs>')
    for i, (x, y, w, h) in enumerate(page["kpi_cards"]):
        parts.append(
            f'    <clipPath id="kpi{i}">'
            f'<rect x="{x + ACCENT_INSET}" y="{y + ACCENT_INSET}" '
            f'width="{w - 2 * ACCENT_INSET}" height="{h - 2 * ACCENT_INSET}" '
            f'rx="{r}"/></clipPath>')
    parts.append('  </defs>')

    for i, (x, y, w, h) in enumerate(page["kpi_cards"]):
        container(x, y, w, h)
        parts.append(
            f'  <rect x="{x + ACCENT_INSET}" y="{y + ACCENT_INSET}" '
            f'width="{ACCENT_W}" height="{h - 2 * ACCENT_INSET}" '
            f'fill="{pal["kpi_accent"]}" clip-path="url(#kpi{i})"/>')

    hx, hy, hw, hh = hdr["rect"]
    parts.append(
        f'  <rect x="{hx}" y="{hy}" width="{hw}" height="{hh}" '
        f'fill="{pal["header_band"]}"/>')
    tx, ty = hdr["text_xy"]
    parts.append(
        f'  <text x="{tx}" y="{ty}" font-family="{hdr["font_stack"]}" '
        f'font-size="{hdr["text_size"]}" font-weight="{hdr["text_weight"]}" '
        f'fill="{hdr["text_color"]}">{hdr["text"]}</text>')
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# PNG - cairosvg when its native library loads, else Pillow
# ---------------------------------------------------------------------------
def try_cairosvg(svg_text, png_path, w, h):
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_text.encode("utf-8"),
                         write_to=png_path, output_width=w, output_height=h)
        return True
    except Exception:
        return False


def pillow_font(size_px, weight):
    from PIL import ImageFont
    fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    # weight 600 -> Segoe UI Semibold; Arial has no 600, bold is the nearest
    candidates = (["seguisb.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"]
                  if weight >= 500 else ["segoeui.ttf", "arial.ttf"])
    for name in candidates:
        path = os.path.join(fonts_dir, name)
        if os.path.isfile(path):
            return ImageFont.truetype(path, size_px)
    return ImageFont.load_default(size_px)


def pillow_png(page, png_path, W, H, s):
    from PIL import Image, ImageChops, ImageDraw
    pal = page["palette"]
    r = pal["container_radius"] * s
    ACCENT_W, ACCENT_INSET = page["accent_w"], page["accent_inset"]
    img = Image.new("RGB", (W, H), pal["page_bg"])
    d = ImageDraw.Draw(img)

    def container(x, y, w, h):
        d.rounded_rectangle([x * s, y * s, (x + w) * s - 1, (y + h) * s - 1],
                            radius=r, fill=pal["container_fill"],
                            outline=pal["container_border"], width=1 * s)

    for x, y, w, h in page["panels"]:
        container(x, y, w, h)

    for x, y, w, h in page["kpi_cards"]:
        container(x, y, w, h)
        # accent bar clipped to the card's rounded corners: intersect a
        # rounded-rect mask (card inset by ACCENT_INSET) with the bar strip
        card = Image.new("L", (W, H), 0)
        ImageDraw.Draw(card).rounded_rectangle(
            [(x + ACCENT_INSET) * s, (y + ACCENT_INSET) * s,
             (x + w - ACCENT_INSET) * s - 1, (y + h - ACCENT_INSET) * s - 1],
            radius=r, fill=255)
        bar = Image.new("L", (W, H), 0)
        ImageDraw.Draw(bar).rectangle(
            [(x + ACCENT_INSET) * s, (y + ACCENT_INSET) * s,
             (x + ACCENT_INSET + ACCENT_W) * s - 1, (y + h - ACCENT_INSET) * s - 1],
            fill=255)
        img.paste(pal["kpi_accent"], (0, 0), ImageChops.multiply(card, bar))

    hdr = page["header"]
    hx, hy, hw, hh = hdr["rect"]
    d.rectangle([hx * s, hy * s, (hx + hw) * s - 1, (hy + hh) * s - 1],
                fill=pal["header_band"])
    tx, ty = hdr["text_xy"]
    d.text((tx * s, ty * s), hdr["text"],
           font=pillow_font(hdr["text_size"] * s, hdr["text_weight"]),
           fill=hdr["text_color"], anchor="ls")
    img.save(png_path)


def main():
    for key, page in PAGES.items():
        cw, ch = page["canvas"]
        s = page["png_scale"]
        m = page["margin"]

        # every container must respect the page margin on the right and bottom
        right = max(x + w for x, y, w, h in page["kpi_cards"] + page["panels"])
        bottom = max(y + h for x, y, w, h in page["kpi_cards"] + page["panels"])
        assert right == cw - m, f"rightmost container ends at {right}, want {cw - m}"
        assert bottom == ch - m, f"lowest container ends at {bottom}, want {ch - m}"
        print(f"margin check: rightmost edge {right} = {cw}-{m}, "
              f"bottom edge {bottom} = {ch}-{m}")
        svg_path = os.path.join(OUT_DIR, f"{key}.svg")
        png_path = os.path.join(OUT_DIR, f"{key}.png")

        svg_text = build_svg(page)
        with open(svg_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg_text)
        print(f"{svg_path}  {cw} x {ch} (SVG user units)")

        W, H = cw * s, ch * s
        if try_cairosvg(svg_text, png_path, W, H):
            renderer = "cairosvg"
        else:
            pillow_png(page, png_path, W, H, s)
            renderer = "Pillow"
        from PIL import Image
        with Image.open(png_path) as im:
            kb = os.path.getsize(png_path) / 1024
            print(f"{png_path}  {im.width} x {im.height} px  "
                  f"{kb:,.0f} KB  [{renderer}]")


if __name__ == "__main__":
    main()
