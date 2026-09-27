"""Draw an original agentdeck mark: a fanned deck of cards with a prompt glyph.

Nothing here derives from upstream's mascot art — the name is the brief, so the
mark is a deck, and the front card carries a terminal prompt.
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

S = 4  # supersample factor
SIZE = 512
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("logo_preview.png")

CARD_W, CARD_H, RADIUS = 214, 300, 30
# A hand of cards fans from a pivot near the bottom, not around each card's own
# centre — otherwise the bottom corners splay apart instead of gathering.
PIVOT_DROP = 128  # how far below centre the fan pivots
CARDS = [  # (angle, top colour, bottom colour)
    (-19, (58, 42, 34), (44, 32, 26)),
    (19, (128, 74, 40), (96, 55, 30)),
    (0, (255, 150, 74), (255, 108, 44)),
]


def gradient_card(
    w: int, h: int, top: tuple[int, int, int], bottom: tuple[int, int, int]
) -> Image.Image:
    """A rounded card filled with a vertical gradient."""
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grad = Image.new("RGB", (w, h))
    gd = ImageDraw.Draw(grad)
    for y in range(h):
        f = y / max(1, h - 1)
        gd.line([(0, y), (w, y)],
                fill=tuple(round(a + (b - a) * f) for a, b in zip(top, bottom, strict=True)))
    shape = Image.new("L", (w, h), 0)
    ImageDraw.Draw(shape).rounded_rectangle((0, 0, w - 1, h - 1), RADIUS * S, fill=255)
    card.paste(grad, (0, 0), shape)
    return card


canvas = Image.new("RGBA", (SIZE * S, SIZE * S), (0, 0, 0, 0))
cx = cy = SIZE * S // 2

pivot = (cx, cy + PIVOT_DROP * S)
for angle, top, bottom in CARDS:
    card = gradient_card(CARD_W * S, CARD_H * S, top, bottom)
    # Hairline edge so the cards stay separated on a dark background.
    edge = Image.new("L", card.size, 0)
    ImageDraw.Draw(edge).rounded_rectangle(
        (0, 0, card.size[0] - 1, card.size[1] - 1), RADIUS * S, outline=255, width=3 * S)
    card.paste(Image.new("RGBA", card.size, (12, 10, 10, 255)), (0, 0), edge)

    rotated = card.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    # Carry the card's centre around the pivot by the same rotation.
    arm = -(PIVOT_DROP * S)  # centre sits this far above the pivot
    theta = math.radians(angle)
    ox = -arm * math.sin(theta)
    oy = arm * math.cos(theta)
    canvas.alpha_composite(
        rotated,
        (round(pivot[0] + ox) - rotated.width // 2,
         round(pivot[1] + oy) - rotated.height // 2))

# Terminal prompt on the front card: a chevron and a caret bar.
d = ImageDraw.Draw(canvas)
stroke = 17 * S
ax, ay = cx - 34 * S, cy - 14 * S
d.line([(ax, ay - 42 * S), (ax + 46 * S, ay), (ax, ay + 42 * S)],
       fill=(24, 16, 12, 255), width=stroke, joint="curve")
d.line([(cx + 6 * S, ay + 42 * S), (cx + 62 * S, ay + 42 * S)],
       fill=(24, 16, 12, 255), width=stroke)

canvas.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(OUT)
print("wrote", OUT)
