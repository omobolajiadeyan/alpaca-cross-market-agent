"""Generate deterministic CrossSignal logo PNGs and the submission cover.

The atmospheric background is generated separately. All typography and the
brand mark are drawn locally so judge-facing text remains exact and repeatable.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BACKGROUND = ASSETS / "crosssignal-cover-background-v2.png"
COVER = ASSETS / "crosssignal-hackathon-cover.png"

NAVY = "#071d49"
INK = "#031126"
CYAN = "#19b5d8"
LIGHT_CYAN = "#72d4e8"
AMBER = "#f6b84a"
WHITE = "#ffffff"
MUTED = "#b9dced"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size)


def bezier(start, control1, control2, end, steps: int = 36):
    points = []
    for index in range(steps + 1):
        t = index / steps
        u = 1 - t
        points.append((
            u ** 3 * start[0] + 3 * u * u * t * control1[0]
            + 3 * u * t * t * control2[0] + t ** 3 * end[0],
            u ** 3 * start[1] + 3 * u * u * t * control1[1]
            + 3 * u * t * t * control2[1] + t ** 3 * end[1],
        ))
    return points


def draw_mark(image: Image.Image, origin: tuple[int, int], size: int) -> None:
    draw = ImageDraw.Draw(image)
    ox, oy = origin
    scale = size / 72

    def point(x, y):
        return ox + x * scale, oy + y * scale

    paths = [
        (10, 31, 35, 0.55), (20, 32, 35, 0.72), (30, 34, 35, 1.0),
        (42, 38, 37, 1.0), (52, 40, 37, 0.72), (62, 41, 37, 0.55),
    ]
    for y, control_y, end_y, opacity in paths:
        color = LIGHT_CYAN if opacity == 1.0 else CYAN
        rgba = (*ImageColor.getrgb(color), int(255 * opacity))
        draw.line(
            bezier(point(5, y), point(22, y), point(24, control_y), point(34, end_y)),
            fill=rgba,
            width=max(2, round(3 * scale)),
            joint="curve",
        )
    draw.line([point(42, 36), point(67, 36)], fill=CYAN,
              width=max(3, round(4 * scale)))
    diamond = [point(38, 29), point(45, 36), point(38, 43), point(31, 36)]
    draw.polygon(diamond, fill=NAVY)
    draw.line(diamond + [diamond[0]], fill=LIGHT_CYAN,
              width=max(2, round(2.5 * scale)), joint="curve")
    r = 2.6 * scale
    cx, cy = point(38, 36)
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=AMBER)
    r = 2.7 * scale
    cx, cy = point(67, 36)
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=LIGHT_CYAN)


def make_mark() -> None:
    scale = 4
    canvas = Image.new("RGBA", (512 * scale, 512 * scale), (0, 0, 0, 0))
    draw_mark(canvas, (0, 0), 512 * scale)
    canvas.resize((512, 512), Image.Resampling.LANCZOS).save(
        ASSETS / "crosssignal-logo-mark.png"
    )


def make_lockup(filename: str, text_color: str, subtitle_color: str) -> None:
    scale = 3
    width, height = 1500 * scale, 360 * scale
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_mark(canvas, (25 * scale, 20 * scale), 310 * scale)
    draw = ImageDraw.Draw(canvas)
    draw.text((360 * scale, 54 * scale), "CROSSSIGNAL",
              font=font("segoeuib.ttf", 120 * scale), fill=text_color)
    draw.text((368 * scale, 205 * scale), "AUDITABLE OPTIONS INTELLIGENCE",
              font=font("segoeui.ttf", 32 * scale), fill=subtitle_color,
              spacing=10 * scale)
    canvas.resize((1500, 360), Image.Resampling.LANCZOS).save(ASSETS / filename)


def cover_background() -> Image.Image:
    source = Image.open(BACKGROUND).convert("RGB")
    target_ratio = 16 / 9
    source_ratio = source.width / source.height
    if source_ratio > target_ratio:
        width = round(source.height * target_ratio)
        left = (source.width - width) // 2
        source = source.crop((left, 0, left + width, source.height))
    else:
        height = round(source.width / target_ratio)
        top = (source.height - height) // 2
        source = source.crop((0, top, source.width, top + height))
    return source.resize((1920, 1080), Image.Resampling.LANCZOS)


def make_cover() -> None:
    image = cover_background().convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    pixels = overlay.load()
    for x in range(1400):
        alpha = int(224 * max(0, 1 - (x / 1450) ** 3))
        for y in range(1080):
            pixels[x, y] = (*ImageColor.getrgb(INK), alpha)
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)

    draw_mark(image, (100, 76), 112)
    draw.text((230, 94), "CROSSSIGNAL", font=font("segoeuib.ttf", 52), fill=WHITE)
    draw.text((234, 154), "AUDITABLE OPTIONS INTELLIGENCE",
              font=font("segoeui.ttf", 17), fill=MUTED)

    draw.rounded_rectangle((104, 302, 558, 350), radius=22,
                           fill=(25, 181, 216, 38), outline=(114, 212, 232, 110), width=1)
    draw.text((130, 316), "ALPACA AI TRADING AGENTS HACKATHON",
              font=font("segoeuib.ttf", 17), fill=LIGHT_CYAN)

    draw.text((102, 398), "Markets disagree.", font=font("segoeuib.ttf", 76), fill=WHITE)
    draw.text((102, 490), "We verify the trade.", font=font("segoeuib.ttf", 76), fill=LIGHT_CYAN)
    draw.multiline_text(
        (108, 626),
        "Six markets. One governed decision.\nDefined-risk options with entry and exit rules fixed in advance.",
        font=font("segoeui.ttf", 29), fill="#d7e7f0", spacing=14,
    )

    draw.line((106, 910, 720, 910), fill=(114, 212, 232, 120), width=2)
    draw.text((106, 936), "OMOBOLAJI E ADEYAN", font=font("segoeuib.ttf", 20), fill=WHITE)
    draw.text((106, 978), "ALPACA PAPER TRADING  •  AUDITABLE ENTRY  •  GOVERNED EXIT",
              font=font("segoeui.ttf", 18), fill=MUTED)
    image.convert("RGB").save(COVER, quality=96)


def main() -> None:
    if not BACKGROUND.exists():
        raise FileNotFoundError(f"Missing background: {BACKGROUND}")
    make_mark()
    make_lockup("crosssignal-logo-lockup-dark.png", WHITE, MUTED)
    make_lockup("crosssignal-logo-lockup-light.png", NAVY, "#53657d")
    make_cover()
    print(f"Generated brand assets in {ASSETS}")


if __name__ == "__main__":
    main()
