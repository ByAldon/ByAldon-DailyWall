# ByAldon DailyWall v0.6.7 fix notes

- Fixed the fake watermark overlay being invisible on Windows 11/VirtualBox.
- The overlay is now topmost by default, click-through, and aligned inside the Windows work area.
- Existing configs are upgraded so `watermark_overlay_topmost` becomes `true`.
- The wallpaper image itself stays untouched when overlay mode is used.
