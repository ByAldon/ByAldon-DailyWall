import json
from pathlib import Path

from wallpaper.bing import fetch_daily_wallpaper_info
from wallpaper.storage import add_to_history, cleanup_old_wallpapers, download_image
from wallpaper.watermark import create_watermarked_wallpaper
from wallpaper.windows import set_wallpaper


CONFIG_FILE = "config.json"
APP_VERSION = "0.6.1"


def load_config():
    """
    Load application settings from config.json.
    """

    config_path = Path(CONFIG_FILE)

    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {CONFIG_FILE}")

    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_config(config):
    """
    Save application settings to config.json.
    """

    config_path = Path(CONFIG_FILE)

    with config_path.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2, ensure_ascii=False)
        file.write("\n")


def should_update_wallpaper(config, was_new):
    """
    Decide if the wallpaper should be applied to Windows.
    """

    set_as_wallpaper = config.get("set_as_wallpaper", True)
    set_wallpaper_mode = config.get("set_wallpaper_mode", "new_only").lower()

    if not set_as_wallpaper:
        return False

    if set_wallpaper_mode == "always":
        return True

    if set_wallpaper_mode == "new_only":
        return was_new

    return was_new


def run_dailywall(logger=print):
    """
    Run the wallpaper update process once.

    Args:
        logger (callable): Function used for status output.

    Returns:
        dict: Run summary.
    """

    config = load_config()

    app_name = config.get("app_name", "ByAldon DailyWall")
    market = config.get("market", "en-US")
    image_resolution = config.get("image_resolution", "UHD")

    original_folder = config.get(
        "wallpaper_original_folder",
        "assets/wallpapers/original"
    )

    watermarked_folder = config.get(
        "wallpaper_watermarked_folder",
        "assets/wallpapers/watermarked"
    )

    history_file = config.get("history_file", "assets/history.json")
    keep_wallpapers = config.get("keep_wallpapers", 30)

    apply_watermark = config.get("apply_watermark", True)
    watermark_text = config.get("watermark_text", "ByAldon DailyWall")
    watermark_icon = config.get("watermark_icon", "assets/icon.png")
    watermark_position = config.get("watermark_position", "bottom_right")
    watermark_opacity = config.get("watermark_opacity", 0.30)
    watermark_scale = config.get("watermark_scale", 0.78)
    watermark_bottom_offset = config.get("watermark_bottom_offset", 42)

    use_uhd = image_resolution.upper() == "UHD"

    logger(f"{app_name} v{APP_VERSION}")
    logger("-" * (len(app_name) + len(APP_VERSION) + 2))
    logger("Fetching today's Bing wallpaper...")

    wallpaper_info = fetch_daily_wallpaper_info(
        market=market,
        use_uhd=use_uhd
    )

    logger(f"Title: {wallpaper_info['title']}")
    logger(f"Copyright: {wallpaper_info['copyright']}")
    logger("Checking original wallpaper folder...")

    original_image_path, was_downloaded = download_image(
        image_url=wallpaper_info["image_url"],
        target_folder=original_folder,
        title=wallpaper_info["title"],
        start_date=wallpaper_info["start_date"]
    )

    if was_downloaded:
        logger("New original wallpaper downloaded.")
    else:
        logger("Original wallpaper already exists locally.")

    logger(f"Original image path: {original_image_path}")

    wallpaper_to_set = original_image_path
    watermarked_image_path = None
    was_watermark_created = False

    if apply_watermark:
        logger("Creating local watermarked copy...")

        watermarked_image_path, was_watermark_created = create_watermarked_wallpaper(
            original_image_path=original_image_path,
            output_folder=watermarked_folder,
            icon_path=watermark_icon,
            watermark_text=watermark_text,
            position=watermark_position,
            opacity=watermark_opacity,
            scale=watermark_scale,
            bottom_offset=watermark_bottom_offset
        )

        wallpaper_to_set = watermarked_image_path

        if was_watermark_created:
            logger("New watermarked wallpaper created.")
        else:
            logger("Watermarked wallpaper already exists locally.")

        logger(f"Watermarked image path: {watermarked_image_path}")
    else:
        logger("Watermark is disabled in config.json.")

    was_new = was_downloaded or was_watermark_created

    history_entry = {
        "date": wallpaper_info["start_date"],
        "title": wallpaper_info["title"],
        "copyright": wallpaper_info["copyright"],
        "image_url": wallpaper_info["image_url"],
        "original_file": str(original_image_path),
        "watermarked_file": str(watermarked_image_path) if watermarked_image_path else "",
        "wallpaper_file": str(wallpaper_to_set),
        "watermark_applied": bool(apply_watermark)
    }

    was_added_to_history = add_to_history(
        history_file=history_file,
        entry=history_entry
    )

    if was_added_to_history:
        logger(f"Added to history: {history_file}")
    else:
        logger("Wallpaper was already in history.")

    deleted_count = cleanup_old_wallpapers(
        history_file=history_file,
        keep_wallpapers=keep_wallpapers
    )

    if deleted_count > 0:
        logger(f"Cleaned up old wallpapers: {deleted_count} file(s) deleted.")
    else:
        logger("No old wallpapers needed cleanup.")

    did_set_wallpaper = False

    if should_update_wallpaper(config, was_new):
        logger("Setting Windows wallpaper...")
        set_wallpaper(wallpaper_to_set)
        did_set_wallpaper = True
        logger("Wallpaper updated successfully.")
    else:
        logger("Skipping wallpaper update.")
        logger("Reason: no new wallpaper was downloaded or created.")

    logger("Done.")

    return {
        "title": wallpaper_info["title"],
        "original_file": str(original_image_path),
        "watermarked_file": str(watermarked_image_path) if watermarked_image_path else "",
        "wallpaper_file": str(wallpaper_to_set),
        "was_downloaded": was_downloaded,
        "was_watermark_created": was_watermark_created,
        "did_set_wallpaper": did_set_wallpaper
    }
