import json
import re
import urllib.request
from pathlib import Path


def ensure_folder(folder_path):
    """
    Create the target folder if it does not exist.
    """

    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def safe_filename(text):
    """
    Convert text to a safe Windows filename.
    """

    text = text.strip()
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    text = re.sub(r"\s+", "_", text)

    if not text:
        text = "bing_wallpaper"

    return text[:120]


def download_image(image_url, target_folder, title="bing_wallpaper", start_date=""):
    """
    Download an image and save it locally.

    Returns:
        tuple:
            Path: local image path
            bool: True if downloaded, False if file already existed
    """

    folder = ensure_folder(target_folder)

    clean_title = safe_filename(title)
    clean_date = safe_filename(start_date) if start_date else "today"

    filename = f"{clean_date}_{clean_title}.jpg"
    target_path = folder / filename

    if target_path.exists():
        return target_path, False

    request = urllib.request.Request(
        image_url,
        headers={
            "User-Agent": "ByAldon DailyWall/0.6.1"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        image_data = response.read()

    if not image_data:
        raise RuntimeError("Downloaded image is empty.")

    target_path.write_bytes(image_data)

    return target_path, True


def load_history(history_file):
    """
    Load wallpaper history from a JSON file.

    Returns:
        list: history entries
    """

    path = Path(history_file)

    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except json.JSONDecodeError:
        return []


def save_history(history_file, history):
    """
    Save wallpaper history to a JSON file.
    """

    path = Path(history_file)
    ensure_folder(path.parent)

    with path.open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=2, ensure_ascii=False)


def add_to_history(history_file, entry):
    """
    Add a wallpaper entry to history if it does not already exist.
    """

    history = load_history(history_file)

    entry_date = entry.get("date")
    entry_original_file = entry.get("original_file")

    for existing_entry in history:
        same_date = existing_entry.get("date") == entry_date

        existing_original = existing_entry.get("original_file")
        existing_legacy_file = existing_entry.get("file")

        same_file = (
            existing_original == entry_original_file
            or existing_legacy_file == entry_original_file
        )

        if same_date and same_file:
            existing_entry.update(entry)
            save_history(history_file, history)
            return False

    history.append(entry)
    save_history(history_file, history)

    return True


def cleanup_old_wallpapers(history_file, keep_wallpapers):
    """
    Keep only the newest wallpapers in history and delete older local files.

    This can delete original and watermarked local copies.
    It does not touch files that are not listed in history.

    Args:
        history_file (str): Path to history.json.
        keep_wallpapers (int): Maximum number of wallpapers to keep.

    Returns:
        int: Number of deleted files.
    """

    if keep_wallpapers is None:
        return 0

    try:
        keep_wallpapers = int(keep_wallpapers)
    except ValueError:
        return 0

    if keep_wallpapers <= 0:
        return 0

    history = load_history(history_file)

    if len(history) <= keep_wallpapers:
        return 0

    sorted_history = sorted(
        history,
        key=lambda item: item.get("date", ""),
        reverse=True
    )

    keep_entries = sorted_history[:keep_wallpapers]
    remove_entries = sorted_history[keep_wallpapers:]

    deleted_count = 0
    paths_to_delete = []

    for entry in remove_entries:
        for key in ["original_file", "watermarked_file", "wallpaper_file", "file"]:
            file_path = entry.get(key)

            if file_path:
                paths_to_delete.append(Path(file_path))

    unique_paths = []

    for path in paths_to_delete:
        if path not in unique_paths:
            unique_paths.append(path)

    for path in unique_paths:
        if path.exists() and path.is_file():
            try:
                path.unlink()
                deleted_count += 1
            except OSError:
                pass

    save_history(history_file, keep_entries)

    return deleted_count