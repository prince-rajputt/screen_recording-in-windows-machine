"""Generates the app icon (assets/icon.ico) and an in-app logo (assets/logo.png)."""
from PIL import Image, ImageDraw

SIZE = 256


def draw_mark(d, box_pad=8, bg=(17, 17, 23, 255), radius=56):
    d.rounded_rectangle([box_pad, box_pad, SIZE - box_pad, SIZE - box_pad], radius=radius, fill=bg)
    d.rounded_rectangle(
        [box_pad, box_pad, SIZE - box_pad, SIZE - box_pad], radius=radius,
        outline=(124, 108, 246, 255), width=6,
    )
    d.rounded_rectangle([56, 64, SIZE - 56, 168], radius=14, outline=(244, 244, 248, 255), width=8)
    d.rectangle([112, 176, SIZE - 112, 188], fill=(244, 244, 248, 255))
    d.rectangle([96, 188, SIZE - 96, 200], fill=(244, 244, 248, 255))
    d.ellipse([SIZE / 2 - 26, 90, SIZE / 2 + 26, 142], fill=(239, 68, 68, 255))


icon_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw_mark(ImageDraw.Draw(icon_img))
icon_img.save("assets/icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

logo_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw_mark(ImageDraw.Draw(logo_img), bg=(28, 26, 46, 255), radius=64)
logo_img.save("assets/logo.png")

print("icon + logo written")
