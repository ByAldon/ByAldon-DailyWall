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
- Includes a system tray app with About, Settings, and Close app
- Settings window includes explanatory text for non-technical users
- Optional startup with Windows
- About window shows the current version and GitHub repository link
- About window can check GitHub releases, including pre-releases, for updates
- Uses your own ByAldon branding only
- No tracking
- No analytics

## Current version

```text
0.6.2
```

## Project structure

```text
assets/
  icon.ico
  icon.png
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

Local runtime files such as `assets/history.json`, downloaded wallpapers, and generated watermarked wallpapers are intentionally ignored by Git.

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

## Tray app

The tray app is the intended end-user direction for ByAldon DailyWall.

### About

The About window shows:

- App name
- Current version
- GitHub repository link
- Check for updates button

The update check compares the local app version with the newest GitHub release. During development it also checks pre-releases.

GitHub repository:

```text
https://github.com/ByAldon/ByAldon-DailyWall
```

### Settings

The Settings window currently includes:

- Start ByAldon DailyWall when Windows starts
- Show ByAldon DailyWall watermark
- Set image as Windows wallpaper
- Wallpaper mode: `new_only` or `always`

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

- Build as standalone `.exe`
- Wallpaper preview
- Unsplash support
- Improved graphical interface

## License

This project is licensed under the MIT License.
