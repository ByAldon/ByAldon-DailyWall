<p align="center">
  <img src="assets/icon.png" alt="ByAldon DailyWall icon" width="128">
</p>

# ByAldon DailyWall

ByAldon DailyWall is a lightweight Windows wallpaper changer.

It downloads the daily Bing wallpaper, saves the original image locally, can create a separate local watermarked copy, and can set the chosen image as the Windows desktop background.

The project is intentionally simple, clean, and transparent about what it does.

## Features

- Downloads the daily Bing wallpaper
- Saves original wallpapers locally
- Creates a separate local watermarked copy by default
- Allows the watermark to be disabled by the user
- Sets the image as the Windows desktop wallpaper
- Keeps a local wallpaper history
- Avoids downloading the same wallpaper twice
- Can skip setting the wallpaper if nothing new was downloaded or created
- Can automatically clean up older local wallpapers
- Includes an early system tray app with About, Settings, and Close app
- Uses your own ByAldon branding only
- No tracking
- No analytics

## Current version

```text
0.6.0
```

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
  app_core.py
  bing.py
  storage.py
  watermark.py
  windows.py

config.json
main.py
tray.py
requirements.txt
README.md
LICENSE
```

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- Pillow
- pystray

Install dependencies with:

```powershell
python -m pip install -r requirements.txt
```

Or manually:

```powershell
python -m pip install pillow pystray
```

## Usage

Run the classic console version:

```powershell
python main.py
```

Run the system tray version:

```powershell
python tray.py
```

The tray version starts the wallpaper update once, then keeps an icon in the Windows notification area.

Right-click the tray icon to open:

```text
About
Settings
Close app
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

  "apply_watermark": true,
  "watermark_text": "ByAldon DailyWall",
  "watermark_icon": "assets/icon.png",
  "watermark_position": "bottom_right",
  "watermark_opacity": 0.30,
  "watermark_scale": 0.78,
  "watermark_bottom_offset": 42
}
```

## Main options

| Setting | Description |
|---|---|
| `app_name` | The application name shown in the terminal. |
| `market` | Bing market/region, for example `en-US`, `nl-NL`, or `de-DE`. |
| `image_resolution` | Use `UHD` for high resolution. |
| `wallpaper_original_folder` | Folder where untouched original wallpapers are stored. |
| `wallpaper_watermarked_folder` | Folder where local watermarked copies are stored. |
| `history_file` | JSON file where local wallpaper history is saved. |
| `set_as_wallpaper` | Set to `true` to update the Windows wallpaper. |
| `set_wallpaper_mode` | Use `new_only` or `always`. |
| `keep_wallpapers` | Maximum number of local wallpapers to keep in history. |

## Watermark options

Watermarking is enabled by default for the final product direction, but it remains the user's choice.

To disable it, set:

```json
"apply_watermark": false
```

Or use the Settings window in the tray app.

| Setting | Description |
|---|---|
| `apply_watermark` | Set to `true` to create and use a local watermarked copy. Set to `false` to use the untouched original image. |
| `watermark_text` | Text shown in the watermark. |
| `watermark_icon` | Path to your own icon used in the watermark. |
| `watermark_position` | Supports `bottom_right`, `bottom_left`, `top_right`, and `top_left`. |
| `watermark_opacity` | Controls watermark transparency. Lower is more subtle. |
| `watermark_scale` | Controls watermark size. Lower is smaller. |
| `watermark_bottom_offset` | Moves bottom-positioned watermarks upward. Useful to avoid the Windows taskbar. |

## About and updates

The tray app currently shows the app name and local version in the About window.

A future version will add GitHub update checking from the About window by comparing the local app version with the latest GitHub release.

## Original and watermarked files

ByAldon DailyWall keeps original downloaded wallpapers untouched:

```text
assets/wallpapers/original/
```

If watermarking is enabled, the app creates a separate local copy:

```text
assets/wallpapers/watermarked/
```

The original image is never modified.

## Privacy

ByAldon DailyWall does not track you, collect personal data, or send analytics.

The app only connects to Bing to fetch the daily wallpaper information and image.

## Independence notice

ByAldon DailyWall is an independent project and is not affiliated with, endorsed by, or sponsored by Microsoft or Bing.

Downloaded images remain subject to their original copyright and licensing terms.

This project does not use Microsoft or Bing logos, icons, or branding as part of its own app identity.

## Planned features

- Better graphical interface
- Better user settings window
- GitHub update check from the About window
- Unsplash support
- Auto-start with Windows
- Wallpaper preview
- Build as standalone `.exe`

## License

This project is licensed under the MIT License.
