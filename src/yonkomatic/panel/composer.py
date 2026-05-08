"""Stage 3: composite Japanese text overlays onto the Gemini-rendered image.

Why this exists: Gemini 3.1 Flash Image hallucinates Japanese characters
when asked to draw multiple speech bubbles in a single image — the symptom
is plausibly-shaped but meaningless kana strings. We instruct Gemini in
``panel/description.py`` to draw NO text/bubbles, then this module composites
PIL-rendered Japanese on top using the dialogue text from the scenario.

Layout is deterministic (no image analysis): each panel is divided into
fixed regions and dialogues are placed by count. Bubble shape is chosen
per-dialogue from ``Dialogue.kind`` (speech/thought/shout), with the
config's ``bubble_style`` controlling only the speech case.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from yonkomatic.config import BubbleStyle, TextRenderMode
from yonkomatic.scenario.schema import DialogueKind, ScenarioEpisode

_BubbleDrawer = Callable[[ImageDraw.ImageDraw, tuple[int, int, int, int], int], None]

# Loading a TrueType/OpenType font involves a syscall and FreeType setup.
# Reusing across panels (and across episodes within one process) is cheap
# and a meaningful win when the font-size fallback loop probes 2-3 sizes.
_FONT_CACHE: dict[tuple[Path, int], ImageFont.FreeTypeFont] = {}

# Punctuation / closing brackets that should not start a line.
_NO_LINE_HEAD = "、。」』）)】"


def compose(
    *,
    image_bytes: bytes,
    episode: ScenarioEpisode,
    mode: TextRenderMode,
    font_path: Path | None = None,
    bubble_style: BubbleStyle = "round",
) -> bytes:
    """Overlay the episode's dialogue onto the rendered image.

    ``mode='never'`` returns image_bytes unchanged. ``'fallback'`` and
    ``'always'`` are equivalent — Gemini is now prompted to leave bubbles
    empty, so there is no distinction between "fall back when needed" and
    "always overlay".
    """
    if mode == "never":
        return image_bytes

    if font_path is None:
        raise RuntimeError("text_rendering.font_path is unset; cannot render Japanese overlay")
    if not font_path.exists():
        raise RuntimeError(
            f"font not found at {font_path}: run `uv run python scripts/install_fonts.py`"
        )

    image = Image.open(BytesIO(image_bytes))
    # Capture format BEFORE convert(); convert() returns a new image whose
    # ``.format`` is None, and we need to round-trip the same MIME so
    # archive/static_site URL extensions stay consistent.
    image_format = image.format or "PNG"
    image.load()
    if image.mode != "RGB":
        image = image.convert("RGB")

    draw = ImageDraw.Draw(image)
    width, height = image.size
    panel_h = height // 4

    for panel in episode.panels:
        if not panel.dialogue:
            continue
        dialogues = panel.dialogue[:4]
        if len(panel.dialogue) > 4:
            print(
                f"[compose] panel {panel.index}: dropping "
                f"{len(panel.dialogue) - 4} dialogue(s) over the 4-bubble layout limit"
            )

        positions = _layout_dialogues(
            count=len(dialogues), panel_w=width, panel_h=panel_h
        )
        y_offset = (panel.index - 1) * panel_h

        for dlg, (cx, cy_local) in zip(dialogues, positions, strict=True):
            _draw_one_bubble(
                image=image,
                draw=draw,
                center=(cx, cy_local + y_offset),
                text=dlg.text,
                kind=dlg.kind,
                speech_style=bubble_style,
                font_path=font_path,
                panel_w=width,
                panel_h=panel_h,
            )

    out = BytesIO()
    if image_format == "JPEG":
        # subsampling=0 (4:4:4) preserves text edge sharpness vs default 4:2:0.
        image.save(out, format="JPEG", quality=95, subsampling=0)
    else:
        image.save(out, format=image_format)
    return out.getvalue()


def _layout_dialogues(*, count: int, panel_w: int, panel_h: int) -> list[tuple[int, int]]:
    """Fixed dialogue centers inside one panel (panel-local y in 0..panel_h)."""
    if count <= 0:
        return []
    if count == 1:
        return [(panel_w // 2, int(panel_h * 0.18))]
    if count == 2:
        return [
            (int(panel_w * 0.27), int(panel_h * 0.18)),
            (int(panel_w * 0.73), int(panel_h * 0.55)),
        ]
    if count == 3:
        return [
            (int(panel_w * 0.25), int(panel_h * 0.16)),
            (int(panel_w * 0.75), int(panel_h * 0.42)),
            (int(panel_w * 0.30), int(panel_h * 0.72)),
        ]
    return [
        (int(panel_w * 0.25), int(panel_h * 0.18)),
        (int(panel_w * 0.75), int(panel_h * 0.30)),
        (int(panel_w * 0.25), int(panel_h * 0.55)),
        (int(panel_w * 0.75), int(panel_h * 0.78)),
    ][:count]


def _load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    key = (font_path, size)
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached
    font = ImageFont.truetype(str(font_path), size)
    _FONT_CACHE[key] = font
    return font


def _wrap_japanese(
    text: str, font: ImageFont.FreeTypeFont, max_width: float
) -> tuple[list[str], list[float]]:
    """Wrap by measured pixel width and return ``(lines, line_widths)``.

    Why width-based instead of fixed column count: at smaller font sizes a
    fixed char count over-fills bubbles; at larger sizes it under-fills.
    Why we accumulate per-character widths instead of remeasuring the
    growing prefix: remeasuring is O(n²) over text length; accumulating
    is O(n). Returning widths lets the caller skip a second pass with
    ``max(font.getlength(line) for line in lines)``.
    """
    if not text:
        return [], []

    lines: list[str] = []
    widths: list[float] = []
    current = ""
    current_w = 0.0
    for ch in text:
        ch_w = font.getlength(ch)
        if current and current_w + ch_w > max_width:
            lines.append(current)
            widths.append(current_w)
            current, current_w = ch, ch_w
        else:
            current += ch
            current_w += ch_w
    if current:
        lines.append(current)
        widths.append(current_w)

    # Naive 禁則: pull line-leading 、。」 back onto previous line and keep
    # widths consistent so callers can rely on ``zip(lines, widths)``.
    fixed_lines: list[str] = []
    fixed_widths: list[float] = []
    for line, width in zip(lines, widths, strict=True):
        if fixed_lines and line and line[0] in _NO_LINE_HEAD:
            head = line[0]
            head_w = font.getlength(head)
            fixed_lines[-1] += head
            fixed_widths[-1] += head_w
            line = line[1:]
            width -= head_w
        if line:
            fixed_lines.append(line)
            fixed_widths.append(width)
    return fixed_lines, fixed_widths


def _draw_one_bubble(
    *,
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    text: str,
    kind: DialogueKind,
    speech_style: BubbleStyle,
    font_path: Path,
    panel_w: int,
    panel_h: int,
) -> None:
    """Probe a font size that fits, then draw the bubble + text together."""
    base_font_size = max(14, int(panel_h * 0.072))
    min_font_size = max(10, int(base_font_size * 0.6))
    max_bubble_w = panel_w * 0.55
    max_bubble_h = panel_h * 0.45

    font_size = base_font_size
    while True:
        font = _load_font(font_path, font_size)
        pad_x = font_size * 0.9
        pad_y = font_size * 0.7
        text_max_w = max_bubble_w - pad_x * 2
        lines, widths = _wrap_japanese(text, font, text_max_w)
        if not lines:
            return

        line_h = font_size * 1.15
        text_w = max(widths)
        text_h = line_h * len(lines)
        bubble_w = text_w + pad_x * 2
        bubble_h = text_h + pad_y * 2

        if (bubble_w <= max_bubble_w and bubble_h <= max_bubble_h) or font_size <= min_font_size:
            break
        font_size = max(min_font_size, int(font_size * 0.9))

    # Cloud and burst outlines extend outside their text-safe inner region.
    # Inflate the bbox so text stays inside the inner ellipse / inside the
    # star's inner radius rather than getting clipped by lobes / spikes.
    if kind == "shout":
        bubble_w *= 1.30
        bubble_h *= 1.30
    elif kind == "thought" or speech_style == "cloud":
        bubble_w *= 1.18
        bubble_h *= 1.18

    cx, cy = center
    half_w = bubble_w / 2
    half_h = bubble_h / 2
    margin = 4
    cx = max(int(half_w + margin), min(image.width - int(half_w + margin), cx))
    cy = max(int(half_h + margin), min(image.height - int(half_h + margin), cy))

    bbox = (
        int(cx - half_w),
        int(cy - half_h),
        int(cx + half_w),
        int(cy + half_h),
    )
    line_w = max(2, int(font_size * 0.12))

    _select_drawer(kind, speech_style)(draw, bbox, line_w)

    draw.multiline_text(
        (cx, cy),
        "\n".join(lines),
        font=font,
        fill=(0, 0, 0),
        anchor="mm",
        align="center",
        spacing=int(font_size * 0.15),
    )


def _draw_ellipse(
    draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], line_w: int
) -> None:
    draw.ellipse(bbox, fill=(255, 255, 255), outline=(0, 0, 0), width=line_w)


def _draw_rectangle(
    draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], line_w: int
) -> None:
    radius = max(8, (bbox[3] - bbox[1]) // 6)
    draw.rounded_rectangle(
        bbox, radius=radius, fill=(255, 255, 255), outline=(0, 0, 0), width=line_w
    )


def _draw_cloud(
    draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], line_w: int
) -> None:
    """Thought-cloud: 8 perimeter lobes overpainted by a central ellipse.

    The lobes are filled+outlined first; the central ellipse (no outline)
    then erases the inner halves of the lobe outlines, leaving only the
    outer scalloped edge visible.
    """
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    half_w = (x1 - x0) / 2
    half_h = (y1 - y0) / 2

    lobe_r = min(half_w, half_h) * 0.32
    n_lobes = 8
    for i in range(n_lobes):
        angle = 2 * math.pi * i / n_lobes
        lx = cx + (half_w - lobe_r * 0.5) * math.cos(angle)
        ly = cy + (half_h - lobe_r * 0.5) * math.sin(angle)
        lobe_bbox = (
            int(lx - lobe_r),
            int(ly - lobe_r),
            int(lx + lobe_r),
            int(ly + lobe_r),
        )
        draw.ellipse(lobe_bbox, fill=(255, 255, 255), outline=(0, 0, 0), width=line_w)

    inner_bbox = (
        int(cx - (half_w - lobe_r * 0.5)),
        int(cy - (half_h - lobe_r * 0.5)),
        int(cx + (half_w - lobe_r * 0.5)),
        int(cy + (half_h - lobe_r * 0.5)),
    )
    draw.ellipse(inner_bbox, fill=(255, 255, 255), outline=None)


def _draw_burst(
    draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], line_w: int
) -> None:
    """Star-shaped burst for ``kind='shout'`` (zigzag border)."""
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    outer_r_x = (x1 - x0) / 2
    outer_r_y = (y1 - y0) / 2
    # Closer to 1.0 = subtler zigzag (more readable). 0.78 = mild burst.
    inner_ratio = 0.78
    n_points = 14

    pts: list[tuple[int, int]] = []
    for i in range(n_points * 2):
        # Start at top (-pi/2) so the burst is oriented up.
        angle = math.pi * i / n_points - math.pi / 2
        if i % 2 == 0:
            r_x, r_y = outer_r_x, outer_r_y
        else:
            r_x, r_y = outer_r_x * inner_ratio, outer_r_y * inner_ratio
        pts.append((int(cx + r_x * math.cos(angle)), int(cy + r_y * math.sin(angle))))

    draw.polygon(pts, fill=(255, 255, 255), outline=(0, 0, 0), width=line_w)


# Speech bubbles use the configurable shape; thought/shout are forced.
_SPEECH_DRAWERS: dict[BubbleStyle, _BubbleDrawer] = {
    "round": _draw_ellipse,
    "rectangle": _draw_rectangle,
    "cloud": _draw_cloud,
}


def _select_drawer(kind: DialogueKind, speech_style: BubbleStyle) -> _BubbleDrawer:
    if kind == "thought":
        return _draw_cloud
    if kind == "shout":
        return _draw_burst
    return _SPEECH_DRAWERS[speech_style]
