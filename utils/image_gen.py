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

# Couleurs par type de bannière
STYLES = {
    "welcome": {
        "top": (35, 25, 70),
        "bottom": (90, 40, 130),
        "accent": (170, 120, 255),
        "title": "BIENVENUE",
    },
    "leave": {
        "top": (40, 20, 25),
        "bottom": (100, 30, 40),
        "accent": (255, 110, 110),
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

    # Toile un peu plus grande pour dessiner l'anneau autour de l'avatar
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


def _add_decorative_circles(base: Image.Image, accent: tuple):
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse((-120, -150, 250, 220), fill=accent + (35,))
    draw.ellipse((WIDTH - 180, HEIGHT - 200, WIDTH + 150, HEIGHT + 100), fill=accent + (35,))
    overlay = overlay.filter(ImageFilter.GaussianBlur(2))
    base.paste(Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB"), (0, 0))


def _fit_text(draw, text, font_path, max_width, start_size, min_size=20):
    size = start_size
    while size > min_size:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(font_path, min_size)


async def generate_card(member, kind: str = "welcome") -> io.BytesIO:
    """kind = 'welcome' ou 'leave'"""
    style = STYLES[kind]
    base = _make_gradient_bg(WIDTH, HEIGHT, style["top"], style["bottom"])
    _add_decorative_circles(base, style["accent"])
    base = base.convert("RGBA")
    draw = ImageDraw.Draw(base)

    # Avatar circulaire à gauche
    avatar_bytes = await fetch_avatar_bytes(member)
    avatar_img = _make_circle_avatar(avatar_bytes, AVATAR_SIZE, style["accent"])
    avatar_x = 70
    avatar_y = (HEIGHT - avatar_img.height) // 2
    base.paste(avatar_img, (avatar_x, avatar_y), avatar_img)

    text_x = avatar_x + avatar_img.width + 50
    max_text_width = WIDTH - text_x - 50

    # Titre (BIENVENUE / AU REVOIR)
    title_font = ImageFont.truetype(FONT_BOLD, 46)
    draw.text((text_x, 110), style["title"], font=title_font, fill=(255, 255, 255))

    # Pseudo, avec taille ajustée pour ne pas déborder
    name = member.display_name
    name_font = _fit_text(draw, name, FONT_BOLD, max_text_width, 54)
    draw.text((text_x, 165), name, font=name_font, fill=style["accent"])

    # Sous-texte
    sub_font = ImageFont.truetype(FONT_REGULAR, 24)
    if kind == "welcome":
        sub_text = f"Membre #{member.guild.member_count}"
    else:
        sub_text = f"Il reste {member.guild.member_count} membres"
    draw.text((text_x, 235), sub_text, font=sub_font, fill=(220, 220, 220))

    buf = io.BytesIO()
    base.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf

