# ByAldon DailyWall

ByAldon DailyWall is a lightweight Windows wallpaper changer that downloads the daily Bing wallpaper, saves it locally, and can set it as your desktop background.

The project is intentionally simple and clean. The core app uses the Python standard library. Optional watermark support requires Pillow.

## Features

- Downloads the daily Bing wallpaper
- Saves original wallpapers locally
- Can create a separate local watermarked copy
- Sets the selected image as the Windows desktop wallpaper
- Keeps a local wallpaper history
- Avoids downloading the same wallpaper twice
- Can skip setting the wallpaper if nothing new was downloaded or created
- Can automatically clean up older wallpapers
- Uses your own optional ByAldon DailyWall watermark only
- No tracking
- No analytics

## Project structure

```text
assets/
  icon.ico
  icon.png
  history.json
  wallpapers/
    .gitkeep
    original/
      .gitkeep
    watermarked/
      .gitkeep

wallpaper/
  bing.py
  storage.py
  watermark.py
  windows.py

.gitignore
config.json
LICENSE
main.py
README.md
```

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- Pillow, only if watermark support is enabled

Install Pillow with:

```powershell
python -m pip install pillow
```

## Usage

Open a terminal in the project folder and run:

```powershell
python main.py
```

Example output:

```text
ByAldon DailyWall v0.5.0
------------------------
Fetching today's Bing wallpaper...
Title: The shape of life at sea
Copyright: ...
Checking original wallpaper folder...
New original wallpaper downloaded.
Original image path: assets\wallpapers\original\20260522_The_shape_of_life_at_sea.jpg
Watermark is disabled in config.json.
Added to history: assets/history.json
No old wallpapers needed cleanup.
Setting Windows wallpaper...
Wallpaper updated successfully.
Done.
```

## Configuration

Settings are stored in `config.json`.

```json
{
  "app_name": "ByAldon DailyWall",
  "market": "en-US",
  "image_resolution": "UHD",

  "wallpaper_original_folder": "assets/wallpapers/original",
  "wallpaper_watermarked_folder": "assets/wallpapers/watermarked",
  "history_file": "assets/history.json",

  "set_as_wallpaper": true,
  "set_wallpaper_mode": "new_only",
  "keep_wallpapers": 30,

  "apply_watermark": false,
  "watermark_text": "ByAldon DailyWall",
  "watermark_icon": "assets/icon.png",
  "watermark_position": "bottom_right",
  "watermark_opacity": 0.35
}
```

### Options

| Setting | Description |
|---|---|
| `app_name` | The application name shown in the terminal. |
| `market` | Bing market/region, for example `en-US`, `nl-NL`, or `de-DE`. |
| `image_resolution` | Use `UHD` for high resolution. |
| `wallpaper_original_folder` | Folder where untouched original wallpapers are stored. |
| `wallpaper_watermarked_folder` | Folder where optional watermarked copies are stored. |
| `history_file` | JSON file where wallpaper history is saved. |
| `set_as_wallpaper` | Set to `true` to update the Windows wallpaper. |
| `set_wallpaper_mode` | Use `new_only` or `always`. |
| `keep_wallpapers` | Maximum number of wallpapers to keep locally. |
| `apply_watermark` | Set to `true` to create and use a local watermarked copy. |
| `watermark_text` | Text shown in the optional watermark. |
| `watermark_icon` | Path to your own watermark icon. |
| `watermark_position` | Supports `bottom_right`, `bottom_left`, `top_right`, and `top_left`. |
| `watermark_opacity` | Opacity from `0.0` to `1.0`. |

## Wallpaper modes

`set_wallpaper_mode` supports two modes:

```text
new_only
```

Only sets the wallpaper when a new image was downloaded or a new watermarked copy was created.

```text
always
```

Always sets the wallpaper, even if the image already exists locally.

## Watermark behavior

Watermarking is disabled by default.

When enabled, ByAldon DailyWall does not overwrite the original downloaded wallpaper. It creates a separate local copy in:

```text
assets/wallpapers/watermarked/
```

The original image stays untouched in:

```text
assets/wallpapers/original/
```

The watermark uses only your own local branding, such as:

```text
assets/icon.png + ByAldon DailyWall
```

## History

ByAldon DailyWall keeps a local history file:

```text
assets/history.json
```

This file stores the date, title, copyright information, image URL, original file path, optional watermarked file path, and the actual wallpaper file path.

## Privacy

ByAldon DailyWall does not track you, collect personal data, or send analytics.

The app only connects to Bing to fetch the daily wallpaper information and image.

## Independence notice

ByAldon DailyWall is an independent project and is not affiliated with, endorsed by, or sponsored by Microsoft or Bing.

Downloaded images remain subject to their original copyright and licensing terms.

This project does not use Microsoft or Bing logos, icons, or branding assets.

## Current version

```text
0.5.0
```

## Planned features

- Graphical interface
- Unsplash support
- Auto-start with Windows
- System tray icon
- Wallpaper preview
- Build as standalone `.exe`

## License

This project is licensed under the MIT License.
