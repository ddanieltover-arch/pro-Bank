"""Generate favicon and OG image assets from ProBank logo files."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import shutil

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
BRAND = STATIC / "brand"
BRAND.mkdir(parents=True, exist_ok=True)

icon = Image.open(STATIC / "emails" / "probank-icon.png").convert("RGBA")
logo_white = Image.open(STATIC / "emails" / "probank-logo-white.png").convert("RGBA")

# Favicon sizes
icon.resize((32, 32), Image.Resampling.LANCZOS).save(BRAND / "favicon-32x32.png")
icon.resize((16, 16), Image.Resampling.LANCZOS).save(BRAND / "favicon-16x16.png")
icon.resize((180, 180), Image.Resampling.LANCZOS).save(BRAND / "apple-touch-icon.png")
icon.save(BRAND / "favicon.png")

icon_16 = icon.resize((16, 16), Image.Resampling.LANCZOS)
icon_32 = icon.resize((32, 32), Image.Resampling.LANCZOS)
icon_48 = icon.resize((48, 48), Image.Resampling.LANCZOS)
icon_32.save(
    BRAND / "favicon.ico",
    format="ICO",
    sizes=[(16, 16), (32, 32), (48, 48)],
    append_images=[icon_16, icon_48],
)

shutil.copy(BRAND / "favicon.ico", STATIC / "favicon.ico")
shutil.copy(BRAND / "favicon.png", STATIC / "favicon.png")
shutil.copy(BRAND / "apple-touch-icon.png", STATIC / "apple-touch-icon.png")

# OG image 1200x630 — dark brand background with white logo
W, H = 1200, 630
bg = Image.new("RGBA", (W, H), (33, 17, 17, 255))  # #211111

glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(glow)
cx, cy = W // 2, H // 2
draw.ellipse([cx - 280, cy - 160, cx + 280, cy + 160], fill=(229, 55, 52, 55))
glow = glow.filter(ImageFilter.GaussianBlur(80))
bg = Image.alpha_composite(bg, glow)

lw, lh = logo_white.size
target_w = 520
scale = target_w / lw
logo = logo_white.resize((int(lw * scale), int(lh * scale)), Image.Resampling.LANCZOS)
lx = (W - logo.width) // 2
ly = (H - logo.height) // 2 - 10
bg.paste(logo, (lx, ly), logo)

try:
    font = ImageFont.truetype("arial.ttf", 28)
except OSError:
    font = ImageFont.load_default()

draw = ImageDraw.Draw(bg)
tagline = "Smart Banking & Refund Solutions"
bbox = draw.textbbox((0, 0), tagline, font=font)
tw = bbox[2] - bbox[0]
draw.text(((W - tw) // 2, ly + logo.height + 28), tagline, fill=(248, 246, 246, 200), font=font)

og = bg.convert("RGB")
og.save(BRAND / "og-image.png", "PNG", optimize=True)
og.save(STATIC / "og-image.png", "PNG", optimize=True)

print("Generated brand assets in", BRAND)
for p in sorted(BRAND.glob("*")):
    print(f"  {p.name}")
