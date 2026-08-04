from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

out = Path(__file__).resolve().parent.parent / "static" / "emails"
out.mkdir(parents=True, exist_ok=True)

# Icon: red rounded square with white bank building mark
size = 160
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
primary = (229, 55, 52, 255)  # #e53734
white = (255, 255, 255, 255)

radius = 36
draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=primary)

# Pediment (triangle roof)
draw.polygon([(40, 58), (80, 38), (120, 58)], fill=white)
# Building body
draw.rectangle([44, 58, 116, 112], fill=white)
# Columns as primary cutouts
for x in (56, 72, 88, 104):
    draw.rectangle([x - 4, 66, x + 4, 104], fill=primary)
# Base steps
draw.rectangle([38, 112, 122, 120], fill=white)
draw.rectangle([34, 120, 126, 128], fill=white)

icon_path = out / "probank-icon.png"
img.save(icon_path, "PNG")
print("wrote", icon_path)

pad = 20
icon_h = 96
icon = img.resize((icon_h, icon_h), Image.Resampling.LANCZOS)
font_paths = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "arialbd.ttf",
]
font = None
for path in font_paths:
    try:
        font = ImageFont.truetype(path, 54)
        break
    except OSError:
        continue
if font is None:
    font = ImageFont.load_default()

text = "ProBank"
tmp = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
td = ImageDraw.Draw(tmp)
bbox = td.textbbox((0, 0), text, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
logo_w = pad + icon_h + 18 + tw + pad
logo_h = pad * 2 + max(icon_h, th)
text_y = (logo_h - th) // 2 - bbox[1]

logo = Image.new("RGBA", (logo_w, logo_h), (0, 0, 0, 0))
logo.paste(icon, (pad, (logo_h - icon_h) // 2), icon)
ImageDraw.Draw(logo).text(
    (pad + icon_h + 18, text_y), text, font=font, fill=(33, 17, 17, 255)
)
logo_path = out / "probank-logo.png"
logo.save(logo_path, "PNG")
print("wrote", logo_path, logo.size)

logo_white = Image.new("RGBA", (logo_w, logo_h), (0, 0, 0, 0))
logo_white.paste(icon, (pad, (logo_h - icon_h) // 2), icon)
ImageDraw.Draw(logo_white).text(
    (pad + icon_h + 18, text_y), text, font=font, fill=(255, 255, 255, 255)
)
logo_white_path = out / "probank-logo-white.png"
logo_white.save(logo_white_path, "PNG")
print("wrote", logo_white_path, logo_white.size)
