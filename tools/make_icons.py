"""Generate the launcher icon and presplash images used by Buildozer.

Only needs Pillow. Run from the project root:

    python tools/make_icons.py

Outputs assets/icon.png (512x512) and assets/presplash.png (1024x1024).
"""

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")

GREEN = (62, 160, 71, 255)
GREEN_DARK = (43, 116, 51, 255)
WHITE = (255, 255, 255, 255)
CARD = (245, 246, 248, 255)
BARS = (62, 160, 71, 255), (41, 151, 255, 255), (255, 152, 0, 255)


def rounded(size, radius, color):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, size, size), radius=radius, fill=color)
    return img


def draw_chart(draw, chart_box):
    """Three ascending bars inside a white card rectangle."""
    left, top, right, bottom = chart_box
    width, height = right - left, bottom - top
    bar_w = width * 0.17
    gap = (width - 3 * bar_w) / 4
    heights = (0.42, 0.62, 0.85)
    for i, (h, color) in enumerate(zip(heights, BARS)):
        x = left + gap + i * (bar_w + gap)
        y_bottom = bottom
        y_top = bottom - height * h
        draw.rounded_rectangle(
            (x, y_top, x + bar_w, y_bottom), radius=bar_w * 0.35, fill=color)
    draw.rounded_rectangle(
        (left + gap * 0.5, bottom, right - gap * 0.5, bottom + height * 0.04),
        radius=4, fill=(120, 125, 132, 255))


def make_icon():
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # green background
    d.rounded_rectangle((0, 0, size, size), radius=110, fill=GREEN)
    # slightly darker shade at the bottom for depth
    d.rounded_rectangle(
        (0, size * 0.72, size, size), radius=110, fill=GREEN_DARK)
    # white card with rounded corners
    card = (size * 0.17, size * 0.20, size * 0.83, size * 0.80)
    d.rounded_rectangle(card, radius=42, fill=CARD)
    # a coin circle behind the bars (allusion to money)
    d.ellipse(
        (size * 0.60, size * 0.18, size * 0.84, size * 0.42), fill=GREEN)
    d.ellipse(
        (size * 0.63, size * 0.21, size * 0.81, size * 0.39),
        outline=WHITE, width=6)
    # rising chart = expenses each week
    chart = (card[0] + size * 0.09, card[1] + size * 0.18,
             card[2] - size * 0.09, card[3] - size * 0.18)
    draw_chart(d, chart)
    img.save(os.path.join(OUT, "icon.png"))


def make_presplash():
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, size, size), radius=196, fill=GREEN)

    # big white rounded card with a bar chart
    card = (size * 0.24, size * 0.22, size * 0.76, size * 0.62)
    d.rounded_rectangle(card, radius=52, fill=CARD)
    chart = (card[0] + size * 0.06, card[1] + size * 0.12,
             card[2] - size * 0.06, card[3] - size * 0.12)
    draw_chart(d, chart)

    # app title below the card
    try:
        font_file = r"C:\Windows\Fonts\arialbd.ttf"
        if not os.path.exists(font_file):
            font_file = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_file, 64)
    except (OSError, IOError):
        font = ImageFont.load_default()
    text = "Kharcha Track"
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    d.text(((size - w) / 2, card[3] + size * 0.06), text,
           font=font, fill=WHITE)
    img.save(os.path.join(OUT, "presplash.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    make_icon()
    make_presplash()
    print("wrote", os.path.join(OUT, "icon.png"),
          "and", os.path.join(OUT, "presplash.png"))