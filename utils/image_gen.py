"""
Génère les bannières de bienvenue / départ.
Compose un fond dégradé + un cercle pour la pp du membre + du texte.
"""
import io
import os
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

WIDTH, HEIGHT = 1000, 400
AVATAR_SIZE = 190

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
FONT_BOLD = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "Poppins-Regular.ttf")
FONT_DISPLAY = os.path.join(FONT_DIR, "ChoretFudyngBubble-Regular.ttf")  # police bubble fun pour le titre + pseudo

BG_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "backgrounds")
# Une seule image utilisée pour bienvenue ET départ. Pour deux images différentes,
# ajoute "welcome.jpg" et "leave.jpg" dans ce dossier : elles seront prioritaires.
BG_DEFAULT = os.path.join(BG_DIR, "background.jpg")

# Couleurs par type de bannière
STYLES = {
    "welcome": {
        "top": (35, 25, 70),
        "bottom": (90, 40, 130),
        "accent": (170, 120, 255),
        "glow": (255, 130, 190),
        "title": "BIENVENUE",
    },
    "leave": {
        "top": (40, 20, 25),
        "bottom": (100, 30, 40),
        "accent": (255, 110, 110),
        "glow": (255, 90, 90),
        "title": "AU REVOIR",
    },
}


async def fetch_avatar_bytes(member) -> bytes:
    url = member.display_avatar.replace(size=256, format="png").url
    async with aiohttp.ClientSession() as session:
        async with session.get(str(url)) as resp:
            return await resp.read()


def _make_circle_avatar(avatar_bytes: bytes, size: int, ring_color: tuple) -> Image.Image:
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = ImageOps.fit(avatar, (size, size), Image.LANCZOS)

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    avatar.putalpha(mask)

    pad = 10
    canvas = Image.new("RGBA", (size + pad * 2, size + pad * 2), (0, 0, 0, 0))
    ring_draw = ImageDraw.Draw(canvas)
    ring_draw.ellipse((0, 0, size + pad * 2, size + pad * 2), outline=ring_color, width=pad)
    canvas.paste(avatar, (pad, pad), avatar)
    return canvas


def _make_gradient_bg(width: int, height: int, top: tuple, bottom: tuple) -> Image.Image:
    base = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / height
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return base


def _resolve_bg_path(kind: str):
    """Cherche une image spécifique (welcome.jpg/leave.jpg), sinon background.jpg, sinon None."""
    for ext in ("jpg", "jpeg", "png"):
        specific = os.path.join(BG_DIR, f"{kind}.{ext}")
        if os.path.exists(specific):
            return specific
    for ext in ("jpg", "jpeg", "png"):
        default = os.path.join(BG_DIR, f"background.{ext}")
        if os.path.exists(default):
            return default
    return None


def _make_photo_bg(path: str, width: int, height: int) -> Image.Image:
    """Recadre la photo au format bannière et assombrit progressivement côté texte (gauche)
    pour garder le pseudo/titre lisibles quelle que soit la photo."""
    img = Image.open(path).convert("RGB")
    img = ImageOps.fit(img, (width, height), Image.LANCZOS).convert("RGBA")

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for x in range(width):
        ratio = 1 - (x / width)
        alpha = int(70 + 130 * ratio)
        draw.line([(x, 0), (x, height)], fill=(8, 6, 15, alpha))
    return Image.alpha_composite(img, overlay).convert("RGB")


def _add_decorative_circles(base: Image.Image, accent: tuple):
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse((-120, -150, 250, 220), fill=accent + (35,))
    draw.ellipse((WIDTH - 180, HEIGHT - 200, WIDTH + 150, HEIGHT + 100), fill=accent + (35,))
    overlay = overlay.filter(ImageFilter.GaussianBlur(2))
    base.paste(Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB"), (0, 0))


def _fit_text(draw, text, font_path, max_width, start_size, min_size=20, stroke_width=0):
    size = start_size
    while size > min_size:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(font_path, min_size)


def _solid_text_layer(text, font, fill_color, stroke_width=0, stroke_fill=None):
    """Rend le texte en une seule couleur (propre et simple), avec contour optionnel."""
    dummy = Image.new("RGBA", (10, 10))
    ddraw = ImageDraw.Draw(dummy)
    bbox = ddraw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    pad = 6
    w = (bbox[2] - bbox[0]) + pad * 2
    h = (bbox[3] - bbox[1]) + pad * 2
    ox, oy = -bbox[0] + pad, -bbox[1] + pad

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(layer)
    if stroke_fill:
        ldraw.text((ox, oy), text, font=font, fill=fill_color, stroke_width=stroke_width, stroke_fill=stroke_fill)
    else:
        ldraw.text((ox, oy), text, font=font, fill=fill_color)
    return layer, bbox


def _paste_text_with_glow(
    base: Image.Image,
    layer: Image.Image,
    pos: tuple,
    glow_color: tuple,
    glow_blur: int = 16,
    glow_alpha: int = 170,
    shadow_blur: int = 6,
    shadow_alpha: int = 110,
    shadow_offset: tuple = (3, 4),
):
    """Empile ombre portée douce -> glow -> texte net, comme un stack After Effects
    (Drop Shadow + Deep Glow). Simple et clair, pas de dégradé multicolore."""
    alpha = layer.split()[-1]

    shadow = Image.new("RGBA", layer.size, (0, 0, 0, shadow_alpha))
    shadow.putalpha(alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
    shadow_canvas = Image.new("RGBA", base.size, (0, 0, 0, 0))
    shadow_canvas.paste(shadow, (pos[0] + shadow_offset[0], pos[1] + shadow_offset[1]), shadow)
    base.alpha_composite(shadow_canvas)

    glow = Image.new("RGBA", layer.size, glow_color + (glow_alpha,))
    glow.putalpha(alpha)
    glow = glow.filter(ImageFilter.GaussianBlur(glow_blur))
    glow_canvas = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_canvas.paste(glow, pos, glow)
    base.alpha_composite(glow_canvas)

    text_canvas = Image.new("RGBA", base.size, (0, 0, 0, 0))
    text_canvas.paste(layer, pos, layer)
    base.alpha_composite(text_canvas)


async def generate_card(member, kind: str = "welcome") -> io.BytesIO:
    """kind = 'welcome' ou 'leave'"""
    style = STYLES[kind]
    bg_path = _resolve_bg_path(kind)
    if bg_path:
        base = _make_photo_bg(bg_path, WIDTH, HEIGHT)
    else:
        base = _make_gradient_bg(WIDTH, HEIGHT, style["top"], style["bottom"])
        _add_decorative_circles(base, style["accent"])
    base = base.convert("RGBA")
    draw = ImageDraw.Draw(base)

    avatar_bytes = await fetch_avatar_bytes(member)
    avatar_img = _make_circle_avatar(avatar_bytes, AVATAR_SIZE, style["accent"])
    avatar_x = 70
    avatar_y = (HEIGHT - avatar_img.height) // 2
    base.paste(avatar_img, (avatar_x, avatar_y), avatar_img)

    text_x = avatar_x + avatar_img.width + 50
    max_text_width = WIDTH - text_x - 50
    glow_color = style["glow"]

    title_font = ImageFont.truetype(FONT_DISPLAY, 76)
    title_layer, _ = _solid_text_layer(style["title"], title_font, (255, 255, 255))
    _paste_text_with_glow(base, title_layer, (text_x, 85), glow_color, glow_blur=18, glow_alpha=180)

    name = member.display_name
    name_font = _fit_text(draw, name, FONT_DISPLAY, max_text_width, 92, min_size=30)
    name_layer, _ = _solid_text_layer(name, name_font, (255, 255, 255))
    _paste_text_with_glow(base, name_layer, (text_x, 175), glow_color, glow_blur=20, glow_alpha=190)

    sub_font = ImageFont.truetype(FONT_REGULAR, 32)
    if kind == "welcome":
        sub_text = f"Membre #{member.guild.member_count}"
    else:
        sub_text = f"Il reste {member.guild.member_count} membres"
    draw.text(
        (text_x, 300),
        sub_text,
        font=sub_font,
        fill=(255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0),
    )

    buf = io.BytesIO()
    base.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf
