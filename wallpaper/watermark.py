from pathlib import Path


def create_watermarked_wallpaper(
    original_image_path,
    output_folder,
    icon_path="assets/icon.png",
    watermark_text="ByAldon DailyWall",
    position="bottom_right",
    opacity=0.30,
    scale=0.78,
    bottom_offset=80,
    margin=None,
    force_recreate=False
):
    """
    Create a local watermarked copy of a wallpaper.

    The original image is never modified.

    Returns:
        tuple:
            Path: path to the watermarked image
            bool: True if created/recreated, False if it already existed
    """

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as error:
        raise RuntimeError(
            "Pillow is required for watermark support. "
            "Install it with: python -m pip install pillow"
        ) from error

    original_path = Path(original_image_path)

    if not original_path.exists():
        raise FileNotFoundError(f"Original wallpaper not found: {original_path}")

    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    watermarked_path = output_path / f"{original_path.stem}_watermarked.jpg"

    if watermarked_path.exists() and not force_recreate:
        return watermarked_path, False

    base_image = Image.open(original_path).convert("RGBA")
    image_width, image_height = base_image.size
    short_side = min(image_width, image_height)

    overlay = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    opacity = max(0.0, min(float(opacity), 1.0))
    scale = max(0.45, min(float(scale), 1.25))
    bottom_offset = max(0, int(bottom_offset))

    font_size = max(16, int(short_side * 0.022 * scale))

    font = None
    possible_fonts = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf"
    ]

    for font_file in possible_fonts:
        if Path(font_file).exists():
            font = ImageFont.truetype(font_file, font_size)
            break

    if font is None:
        font = ImageFont.load_default()

    icon = None
    icon_file = Path(icon_path)

    if icon_file.exists():
        icon = Image.open(icon_file).convert("RGBA")
        icon_size = max(22, int(short_side * 0.036 * scale))
        icon.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)

    text = watermark_text.strip() if watermark_text else ""

    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    icon_width = icon.width if icon else 0
    icon_height = icon.height if icon else 0

    gap = max(8, int(short_side * 0.006 * scale))
    padding_x = max(14, int(short_side * 0.011 * scale))
    padding_y = max(10, int(short_side * 0.008 * scale))

    content_width = icon_width + (gap if icon and text else 0) + text_width
    content_height = max(icon_height, text_height)

    box_width = content_width + padding_x * 2
    box_height = content_height + padding_y * 2

    if margin is None:
        margin = max(18, int(short_side * 0.018))
    else:
        margin = max(18, int(margin))

    position = position.lower()

    if position == "bottom_left":
        box_x = margin
        box_y = image_height - box_height - margin - bottom_offset
    elif position == "top_left":
        box_x = margin
        box_y = margin
    elif position == "top_right":
        box_x = image_width - box_width - margin
        box_y = margin
    else:
        box_x = image_width - box_width - margin
        box_y = image_height - box_height - margin - bottom_offset

    box_x = max(0, box_x)
    box_y = max(0, box_y)

    box_alpha = int(145 * opacity)
    text_alpha = int(255 * opacity)
    icon_alpha = int(255 * opacity)

    radius = max(10, int(box_height * 0.26))

    draw.rounded_rectangle(
        [box_x, box_y, box_x + box_width, box_y + box_height],
        radius=radius,
        fill=(0, 0, 0, box_alpha)
    )

    cursor_x = box_x + padding_x
    center_y = box_y + box_height // 2

    if icon:
        icon_layer = Image.new("RGBA", icon.size, (0, 0, 0, 0))
        icon_layer.alpha_composite(icon)

        icon_alpha_layer = icon_layer.getchannel("A").point(
            lambda value: int(value * (icon_alpha / 255))
        )
        icon_layer.putalpha(icon_alpha_layer)

        icon_y = center_y - icon.height // 2
        overlay.alpha_composite(icon_layer, (cursor_x, icon_y))
        cursor_x += icon.width + gap

    if text:
        text_y = center_y - text_height // 2 - text_bbox[1]

        draw.text(
            (cursor_x, text_y),
            text,
            font=font,
            fill=(255, 255, 255, text_alpha)
        )

    final_image = Image.alpha_composite(base_image, overlay).convert("RGB")
    final_image.save(watermarked_path, "JPEG", quality=95, optimize=True)

    return watermarked_path, True
