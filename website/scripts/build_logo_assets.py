"""Build SRIVATSANKA logo variants from the provided master PNG."""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
BRAND = PUBLIC / "brand"
SOURCE = Path(
    r"C:\Users\farna\.cursor\projects\c-Users-farna-OneDrive-Desktop-Kannans\assets"
    r"\c__Users_farna_AppData_Roaming_Cursor_User_workspaceStorage_99480f5090fcec3de701c0323f7ea509"
    r"_images_logo-ed006bae-1853-4fc4-a538-528e1bfb3f8a.png"
)
if not SOURCE.exists():
    SOURCE = PUBLIC / "logo.png"

EMERALD = "#0B6B3A"
FRESH = "#7AC943"
ICON_SCALE = 0.85  # 15% smaller in layout


def remove_black_bg(im: Image.Image, threshold: int = 45) -> Image.Image:
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r < threshold and g < threshold and b < threshold:
                px[x, y] = (r, g, b, 0)
    return im


def crop_non_transparent(im: Image.Image, pad: int = 8) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        return im
    L, T, R, B = bbox
    L = max(0, L - pad)
    T = max(0, T - pad)
    R = min(im.width, R + pad)
    B = min(im.height, B + pad)
    return im.crop((L, T, R, B))


def extract_icon(full: Image.Image) -> Image.Image:
    """Top ~52% is the icon in the master artwork."""
    w, h = full.size
    icon_h = int(h * 0.52)
    icon = full.crop((0, 0, w, icon_h))
    return crop_non_transparent(icon, pad=4)


def png_to_data_uri(path: Path) -> str:
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{b64}"


def write_svg_vertical(icon_uri: str, out: Path) -> None:
    # Icon drawn at 140×88 then scaled 0.85 (15% smaller), centered above wordmark
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 280 180" role="img" aria-label="SRIVATSANKA">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500&amp;family=Playfair+Display:wght@600;700&amp;display=swap');
      .brand {{ font-family: 'Playfair Display', Georgia, serif; font-weight: 700; fill: {EMERALD}; letter-spacing: 0.11em; }}
      .tag {{ font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 500; fill: {EMERALD}; letter-spacing: 0.035em; }}
    </style>
  </defs>
  <g transform="translate(140 46) scale({ICON_SCALE}) translate(-70 -44)">
    <image xlink:href="{icon_uri}" width="140" height="88" preserveAspectRatio="xMidYMid meet"/>
  </g>
  <text class="brand" x="140" y="114" text-anchor="middle" font-size="20">SRIVATSANKA</text>
  <text class="tag" x="140" y="134" text-anchor="middle" font-size="8.8">
    <tspan x="140" dy="0">Pure Veg Catering Services</tspan>
    <tspan x="140" dy="11">for All Occasions</tspan>
  </text>
</svg>"""
    out.write_text(svg, encoding="utf-8")


def write_svg_horizontal(icon_uri: str, out: Path) -> None:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 480 100" role="img" aria-label="SRIVATSANKA">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500&amp;family=Playfair+Display:wght@600;700&amp;display=swap');
      .brand {{ font-family: 'Playfair Display', Georgia, serif; font-weight: 700; fill: {EMERALD}; letter-spacing: 0.12em; }}
      .tag {{ font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 500; fill: {EMERALD}; letter-spacing: 0.04em; }}
    </style>
  </defs>
  <g transform="translate(42 50) scale({ICON_SCALE}) translate(-38 -38)">
    <image xlink:href="{icon_uri}" width="76" height="76" preserveAspectRatio="xMidYMid meet"/>
  </g>
  <text class="brand" x="92" y="48" font-size="26">SRIVATSANKA</text>
  <text class="tag" x="94" y="72" font-size="11.5">Pure Veg Catering Services for All Occasions</text>
</svg>"""
    out.write_text(svg, encoding="utf-8")


def write_svg_favicon(icon_uri: str, out: Path) -> None:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 64 64" role="img" aria-label="SRIVATSANKA">
  <g transform="translate(32 32) scale({ICON_SCALE}) translate(-28 -28)">
    <image xlink:href="{icon_uri}" width="56" height="56" preserveAspectRatio="xMidYMid meet"/>
  </g>
</svg>"""
    out.write_text(svg, encoding="utf-8")


def rasterize_layout(icon: Image.Image, mode: str, size: tuple[int, int]) -> Image.Image:
    """Compose flat PNG without glow/outline on text (PIL text)."""
    from PIL import ImageDraw, ImageFont

    W, H = size
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    icon_scaled = icon.copy()
    iw, ih = icon.size

    if mode == "vertical":
        icon_w = int(W * 0.50 * ICON_SCALE)
        icon_h = int(icon_w * ih / iw)
        icon_scaled = icon_scaled.resize((icon_w, icon_h), Image.Resampling.LANCZOS)
        ix = (W - icon_w) // 2
        iy = int(H * 0.06)
        canvas.paste(icon_scaled, (ix, iy), icon_scaled)
        draw = ImageDraw.Draw(canvas)
        try:
            font_b = ImageFont.truetype("arial.ttf", int(H * 0.11))
            font_t = ImageFont.truetype("arial.ttf", int(H * 0.055))
        except OSError:
            font_b = ImageFont.load_default()
            font_t = font_b
        name = "SRIVATSANKA"
        tw = draw.textlength(name, font=font_b)
        draw.text(((W - tw) / 2, iy + icon_h + 10), name, fill=(11, 107, 58, 255), font=font_b)
        tag1, tag2 = "Pure Veg Catering Services", "for All Occasions"
        t1w = draw.textlength(tag1, font=font_t)
        t2w = draw.textlength(tag2, font=font_t)
        draw.text(((W - t1w) / 2, iy + icon_h + 34), tag1, fill=(11, 107, 58, 230), font=font_t)
        draw.text(((W - t2w) / 2, iy + icon_h + 48), tag2, fill=(11, 107, 58, 230), font=font_t)
    elif mode == "horizontal":
        icon_w = int(H * 0.72 * ICON_SCALE)
        icon_h = int(icon_w * ih / iw)
        icon_scaled = icon_scaled.resize((icon_w, icon_h), Image.Resampling.LANCZOS)
        canvas.paste(icon_scaled, (8, (H - icon_h) // 2), icon_scaled)
        draw = ImageDraw.Draw(canvas)
        try:
            font_b = ImageFont.truetype("arial.ttf", int(H * 0.22))
            font_t = ImageFont.truetype("arial.ttf", int(H * 0.10))
        except OSError:
            font_b = ImageFont.load_default()
            font_t = font_b
        draw.text((icon_w + 20, int(H * 0.28)), "SRIVATSANKA", fill=(11, 107, 58, 255), font=font_b)
        draw.text((icon_w + 22, int(H * 0.58)), "Pure Veg Catering Services for All Occasions", fill=(11, 107, 58, 230), font=font_t)
    else:  # favicon
        icon_scaled = icon_scaled.resize((H - 8, H - 8), Image.Resampling.LANCZOS)
        canvas.paste(icon_scaled, (4, 4), icon_scaled)

    return canvas


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    master = Image.open(SOURCE)
    full = remove_black_bg(master)
    icon = extract_icon(full)
    icon_path = BRAND / "icon-symbol.png"
    icon.save(icon_path, "PNG")

    uri = png_to_data_uri(icon_path)
    write_svg_vertical(uri, BRAND / "logo-sidebar.svg")
    write_svg_horizontal(uri, BRAND / "logo-horizontal.svg")
    write_svg_favicon(uri, BRAND / "logo-icon.svg")
    (BRAND / "logo.svg").write_text((BRAND / "logo-horizontal.svg").read_text(encoding="utf-8"), encoding="utf-8")

    # Mono favicon-style (icon only, same asset)
    write_svg_favicon(uri, BRAND / "logo-mono.svg")

    # High-res PNG exports (4K vertical, 2K horizontal)
    rasterize_layout(icon, "vertical", (1120, 720)).save(BRAND / "logo-sidebar.png", "PNG")
    rasterize_layout(icon, "horizontal", (3840, 800)).save(BRAND / "logo-horizontal-4k.png", "PNG")
    rasterize_layout(icon, "horizontal", (960, 200)).save(BRAND / "logo-horizontal.png", "PNG")
    rasterize_layout(icon, "favicon", (512, 512)).save(BRAND / "logo-icon.png", "PNG")
    rasterize_layout(icon, "vertical", (1120, 720)).save(PUBLIC / "logo.png", "PNG")

    print("Built:", BRAND)
    print("Icon size in layouts uses 85% scale. Source:", SOURCE)


if __name__ == "__main__":
    main()
