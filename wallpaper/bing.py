import json
import urllib.request
from urllib.parse import urljoin


BING_BASE_URL = "https://www.bing.com"
BING_ARCHIVE_URL = "https://www.bing.com/HPImageArchive.aspx"


def fetch_daily_wallpaper_info(market="en-US", use_uhd=True):
    """
    Fetch today's Bing wallpaper information.

    Returns:
        dict: {
            "title": str,
            "copyright": str,
            "image_url": str,
            "start_date": str,
            "raw": dict
        }
    """

    uhd_value = "1" if use_uhd else "0"

    url = (
        f"{BING_ARCHIVE_URL}"
        f"?format=js"
        f"&idx=0"
        f"&n=1"
        f"&mkt={market}"
        f"&uhd={uhd_value}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ByAldon DailyWall/0.6.1"
        }
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read().decode("utf-8")

    parsed = json.loads(data)

    if "images" not in parsed or not parsed["images"]:
        raise RuntimeError("No Bing wallpaper image data found.")

    image_data = parsed["images"][0]

    relative_image_url = image_data.get("url")
    if not relative_image_url:
        raise RuntimeError("No image URL found in Bing response.")

    image_url = urljoin(BING_BASE_URL, relative_image_url)

    return {
        "title": image_data.get("title", "Bing Daily Wallpaper"),
        "copyright": image_data.get("copyright", ""),
        "image_url": image_url,
        "start_date": image_data.get("startdate", ""),
        "raw": image_data
    }