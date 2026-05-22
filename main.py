import json
import sys
from pathlib import Path

from wallpaper.bing import fetch_daily_wallpaper_info
from wallpaper.storage import add_to_history, cleanup_old_wallpapers, download_image
from wallpaper.watermark import create_watermarked_wallpaper
from wallpaper.windows import set_wallpaper


CONFIG_FILE = "config.json"
APP_VERSION = "0.5.1"


def load_config():
    """
    Load application settings from config.json.
    """

    config_path = Path(CONFIG_FILE)

    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {CONFIG_FILE}")

    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


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

    print(f"Unknown set_wallpaper_mode: {set_wallpaper_mode}")
    print("Falling back to 'new_only' behavior.")

    return was_new


def main():
    try:
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

        apply_watermark = config.get("apply_watermark", False)
        watermark_text = config.get("watermark_text", "ByAldon DailyWall")
        watermark_icon = config.get("watermark_icon", "assets/icon.png")
        watermark_position = config.get("watermark_position", "bottom_right")
        watermark_opacity = config.get("watermark_opacity", 0.30)
        watermark_scale = config.get("watermark_scale", 0.78)
        watermark_bottom_offset = config.get("watermark_bottom_offset", 42)

        use_uhd = image_resolution.upper() == "UHD"

        print(f"{app_name} v{APP_VERSION}")
        print("-" * (len(app_name) + len(APP_VERSION) + 2))
        print("Fetching today's Bing wallpaper...")

        wallpaper_info = fetch_daily_wallpaper_info(
            market=market,
            use_uhd=use_uhd
        )

        print(f"Title: {wallpaper_info['title']}")
        print(f"Copyright: {wallpaper_info['copyright']}")
        print("Checking original wallpaper folder...")

        original_image_path, was_downloaded = download_image(
            image_url=wallpaper_info["image_url"],
            target_folder=original_folder,
            title=wallpaper_info["title"],
            start_date=wallpaper_info["start_date"]
        )

        if was_downloaded:
            print("New original wallpaper downloaded.")
        else:
            print("Original wallpaper already exists locally.")

        print(f"Original image path: {original_image_path}")

        wallpaper_to_set = original_image_path
        watermarked_image_path = None
        was_watermark_created = False

        if apply_watermark:
            print("Creating local watermarked copy...")

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
                print("New watermarked wallpaper created.")
            else:
                print("Watermarked wallpaper already exists locally.")

            print(f"Watermarked image path: {watermarked_image_path}")
        else:
            print("Watermark is disabled in config.json.")

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
            print(f"Added to history: {history_file}")
        else:
            print("Wallpaper was already in history.")

        deleted_count = cleanup_old_wallpapers(
            history_file=history_file,
            keep_wallpapers=keep_wallpapers
        )

        if deleted_count > 0:
            print(f"Cleaned up old wallpapers: {deleted_count} file(s) deleted.")
        else:
            print("No old wallpapers needed cleanup.")

        if should_update_wallpaper(config, was_new):
            print("Setting Windows wallpaper...")
            set_wallpaper(wallpaper_to_set)
            print("Wallpaper updated successfully.")
        else:
            print("Skipping wallpaper update.")
            print("Reason: no new wallpaper was downloaded or created.")

        print("Done.")

    except Exception as error:
        print("Something went wrong:")
        print(error)
        sys.exit(1)


if __name__ == "__main__":
    main()
