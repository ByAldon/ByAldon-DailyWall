import json
import os
import sys
from pathlib import Path

from wallpaper.bing import fetch_daily_wallpaper_info
from wallpaper.storage import add_to_history, cleanup_old_wallpapers, download_image
from wallpaper.watermark import create_watermarked_wallpaper
from wallpaper.windows import set_wallpaper


APP_NAME = "ByAldon DailyWall"
CONFIG_FILE = "config.json"
APP_VERSION = "0.6.12"


def get_app_base_path():
    """
    Return the folder where the app itself lives.

    In development this is the project folder. In a packaged EXE this is the
    folder where the EXE was started from. Do not use this for user-writable
    files such as config, history, or downloaded wallpapers.
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


def get_resource_base_path():
    """
    Return the folder that contains bundled read-only resources.

    PyInstaller one-file builds unpack bundled files into sys._MEIPASS. In
    development, resources live in the project folder.
    """

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()

    return get_app_base_path()


def resource_path(relative_path):
    """
    Convert a project-relative resource path to an absolute path.

    Use this for bundled files like assets/icon.png.
    """

    return get_resource_base_path() / relative_path


def get_user_data_path():
    """
    Return the writable per-user app data folder.

    This fixes the VM/installer issue where the app expected config.json next
    to the EXE or on the Desktop. Windows apps should store user settings and
    downloaded data in AppData, not beside the executable.
    """

    appdata = os.environ.get("APPDATA")

    if appdata:
        base_path = Path(appdata)
    else:
        base_path = Path.home() / "AppData" / "Roaming"

    user_data_path = base_path / APP_NAME
    user_data_path.mkdir(parents=True, exist_ok=True)
    return user_data_path


def app_path(relative_path):
    """
    Backward-compatible helper for files beside the app.
    """

    return get_app_base_path() / relative_path


def user_data_path(relative_path):
    """
    Convert a path relative to the app's writable data folder to an absolute path.
    """

    return get_user_data_path() / relative_path


def resolve_config_path():
    """
    Return the full path to the writable config.json.
    """

    return get_user_data_path() / CONFIG_FILE


def create_default_config():
    """
    Create the default configuration for a fresh install.
    """

    return {
        "app_name": APP_NAME,
        "market": "en-US",
        "image_resolution": "UHD",
        "wallpaper_original_folder": str(user_data_path("wallpapers/original")),
        "wallpaper_watermarked_folder": str(user_data_path("wallpapers/watermarked")),
        "history_file": str(user_data_path("history.json")),
        "set_as_wallpaper": True,
        "set_wallpaper_mode": "always",
        "keep_wallpapers": 30,
        "apply_watermark": True,
        "watermark_text": "ByAldon DailyWall",
        "watermark_icon": str(resource_path("assets/icon.png")),
        "watermark_position": "top_right",
        "watermark_opacity": 0.70,
        "watermark_scale": 0.86,
        "watermark_bottom_offset": 190,
        "watermark_margin": 70,
        "watermark_mode": "burned_in",
        "watermark_overlay_margin": 32,
        "watermark_overlay_topmost": True
    }


def ensure_config_exists():
    """
    Create config.json automatically when it does not exist.
    """

    config_path = resolve_config_path()

    if config_path.exists():
        return config_path

    default_config = create_default_config()
    save_config(default_config)
    return config_path


def normalize_config_paths(config):
    """
    Make paths absolute and safe for runtime use.

    Downloaded wallpapers, history, and config are user data and should be
    writable. Bundled files such as the watermark icon are treated as resources.
    """

    normalized = dict(config)

    writable_path_keys = [
        "wallpaper_original_folder",
        "wallpaper_watermarked_folder",
        "history_file"
    ]

    for key in writable_path_keys:
        value = normalized.get(key)

        if not value:
            continue

        path = Path(value)

        if not path.is_absolute():
            # Keep old relative configs working, but resolve them into AppData
            # instead of writing beside the EXE or into Program Files.
            parts = list(path.parts)
            if parts and parts[0].lower() == "assets":
                parts = parts[1:]
            normalized[key] = str(user_data_path(Path(*parts)))

    watermark_icon = normalized.get("watermark_icon")

    if watermark_icon:
        icon_path = Path(watermark_icon)
        if not icon_path.is_absolute():
            normalized["watermark_icon"] = str(resource_path(watermark_icon))

    return normalized


def load_config():
    """
    Load application settings from the writable AppData config.json.

    On first run, the config is created automatically so the EXE works on a
    clean Windows VM without manually copying config.json.
    """

    config_path = ensure_config_exists()

    try:
        with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except json.JSONDecodeError as error:
        broken_path = config_path.with_suffix(".broken.json")
        try:
            config_path.replace(broken_path)
        except OSError:
            pass

        config = create_default_config()
        save_config(config)
        raise RuntimeError(
            f"The config file was invalid and has been reset. "
            f"Old file: {broken_path}"
        ) from error

    default_config = create_default_config()
    changed = False

    for key, value in default_config.items():
        if key not in config:
            config[key] = value
            changed = True

    # Upgrade older configs that used a very subtle watermark and placed it
    # close to the taskbar. This keeps existing user choices for other values.
    if config.get("watermark_opacity") == 0.3:
        config["watermark_opacity"] = default_config["watermark_opacity"]
        changed = True

    # v0.6.9: burned-in watermark needs to sit higher because the Windows
    # taskbar covers the bottom part of the wallpaper.
    if int(config.get("watermark_bottom_offset", 0) or 0) < 160:
        config["watermark_bottom_offset"] = default_config["watermark_bottom_offset"]
        changed = True

    # v0.6.11: give the top-right watermark more breathing room from the edges.
    if int(config.get("watermark_margin", 0) or 0) < 60:
        config["watermark_margin"] = default_config["watermark_margin"]
        changed = True

    # v0.6.10: move the default burned-in watermark to the top-right corner.
    # This avoids the taskbar entirely and usually stays away from desktop icons.
    if (
        config.get("watermark_mode", "burned_in") == "burned_in"
        and config.get("watermark_position") == "bottom_right"
    ):
        config["watermark_position"] = default_config["watermark_position"]
        changed = True

    # v0.6.7: the overlay must be topmost, otherwise Windows can place it
    # behind the desktop/Progman layer and it becomes invisible on some PCs/VMs.
    if config.get("watermark_mode", "overlay") == "overlay" and config.get("watermark_overlay_topmost") is not True:
        config["watermark_overlay_topmost"] = True
        changed = True

    if int(config.get("watermark_overlay_margin", 0) or 0) < 32:
        config["watermark_overlay_margin"] = default_config["watermark_overlay_margin"]
        changed = True

    if changed:
        save_config(config)

    return config


def load_runtime_config():
    """
    Load config and normalize paths for runtime use.
    """

    return normalize_config_paths(load_config())


def save_config(config):
    """
    Save application settings to the writable AppData config.json.
    """

    config_path = resolve_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

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


def run_dailywall(logger=print, force_apply=False):
    """
    Run the wallpaper update process once.

    Args:
        logger (callable): Function used for status output.

    Returns:
        dict: Run summary.
    """

    config = load_runtime_config()

    app_name = config.get("app_name", APP_NAME)
    market = config.get("market", "en-US")
    image_resolution = config.get("image_resolution", "UHD")

    original_folder = config.get(
        "wallpaper_original_folder",
        str(user_data_path("wallpapers/original"))
    )

    watermarked_folder = config.get(
        "wallpaper_watermarked_folder",
        str(user_data_path("wallpapers/watermarked"))
    )

    history_file = config.get("history_file", str(user_data_path("history.json")))
    keep_wallpapers = config.get("keep_wallpapers", 30)

    apply_watermark = config.get("apply_watermark", True)
    watermark_text = config.get("watermark_text", APP_NAME)
    watermark_icon = config.get("watermark_icon", str(resource_path("assets/icon.png")))
    watermark_position = config.get("watermark_position", "bottom_right")
    watermark_opacity = config.get("watermark_opacity", 0.70)
    watermark_scale = config.get("watermark_scale", 0.78)
    watermark_bottom_offset = config.get("watermark_bottom_offset", 190)
    watermark_margin = config.get("watermark_margin", 70)
    watermark_mode = str(config.get("watermark_mode", "overlay")).lower()

    use_uhd = image_resolution.upper() == "UHD"

    logger(f"{app_name} v{APP_VERSION}")
    logger("-" * (len(app_name) + len(APP_VERSION) + 2))
    logger(f"Config: {resolve_config_path()}")
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

    if apply_watermark and watermark_mode == "burned_in":
        logger("Creating local watermarked copy...")

        watermarked_image_path, was_watermark_created = create_watermarked_wallpaper(
            original_image_path=original_image_path,
            output_folder=watermarked_folder,
            icon_path=watermark_icon,
            watermark_text=watermark_text,
            position=watermark_position,
            opacity=watermark_opacity,
            scale=watermark_scale,
            bottom_offset=watermark_bottom_offset,
            margin=watermark_margin,
            force_recreate=True
        )

        wallpaper_to_set = watermarked_image_path

        if was_watermark_created:
            logger("Watermarked wallpaper created or refreshed.")
        else:
            logger("Watermarked wallpaper already exists locally.")

        logger(f"Watermarked image path: {watermarked_image_path}")
    elif apply_watermark:
        logger("Watermark overlay is enabled. The wallpaper image stays untouched.")
    else:
        logger("Watermark is disabled in settings.")

    was_new = was_downloaded or was_watermark_created

    history_entry = {
        "date": wallpaper_info["start_date"],
        "title": wallpaper_info["title"],
        "copyright": wallpaper_info["copyright"],
        "image_url": wallpaper_info["image_url"],
        "original_file": str(original_image_path),
        "watermarked_file": str(watermarked_image_path) if watermarked_image_path else "",
        "wallpaper_file": str(wallpaper_to_set),
        "watermark_applied": bool(apply_watermark),
        "watermark_mode": watermark_mode
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

    if force_apply or should_update_wallpaper(config, was_new):
        logger("Setting Windows wallpaper...")
        did_set_wallpaper = set_wallpaper(wallpaper_to_set)
        logger("Wallpaper updated successfully.")
    else:
        logger("Windows wallpaper was not changed because of the current settings.")

    return {
        "app_name": app_name,
        "version": APP_VERSION,
        "config_file": str(resolve_config_path()),
        "title": wallpaper_info["title"],
        "original_file": str(original_image_path),
        "watermarked_file": str(watermarked_image_path) if watermarked_image_path else "",
        "wallpaper_file": str(wallpaper_to_set),
        "was_downloaded": was_downloaded,
        "was_watermark_created": was_watermark_created,
        "was_added_to_history": was_added_to_history,
        "deleted_count": deleted_count,
        "did_set_wallpaper": did_set_wallpaper
    }
