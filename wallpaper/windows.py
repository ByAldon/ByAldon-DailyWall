import ctypes
from pathlib import Path


SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


def set_wallpaper(image_path):
    """
    Set the Windows desktop wallpaper.

    Args:
        image_path (str | Path): Path to the image file.

    Returns:
        bool: True when Windows accepted the wallpaper change.
    """

    path = Path(image_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Wallpaper file not found: {path}")

    result = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER,
        0,
        str(path),
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )

    if not result:
        raise RuntimeError("Windows did not accept the wallpaper change.")

    return True