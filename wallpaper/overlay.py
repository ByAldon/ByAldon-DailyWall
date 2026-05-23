import ctypes
import threading
from pathlib import Path


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


SPI_GETWORKAREA = 0x0030
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2


class WatermarkOverlay:
    """
    A fake desktop watermark that floats above the wallpaper instead of being
    burned into the wallpaper image.

    This is intentionally click-through, so it does not block desktop icons or
    normal mouse clicks. Positioning is based on the Windows work area, which is
    the screen area excluding the taskbar.
    """

    def __init__(self):
        self.root = None
        self.label = None
        self.photo = None
        self.thread = None
        self.lock = threading.Lock()
        self.pending_config = None
        self.ready = threading.Event()
        self.is_visible = False

    def start(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                return

            self.thread = threading.Thread(target=self._run_tk, daemon=True)
            self.thread.start()

    def show(self, config):
        self.start()
        self.pending_config = dict(config)

        if self.ready.wait(timeout=3) and self.root:
            self.root.after(0, self._apply_pending_config)

    def hide(self):
        if self.ready.is_set() and self.root:
            self.root.after(0, self._hide)

    def refresh(self, config):
        if config.get("apply_watermark", True) and config.get("watermark_mode", "overlay") == "overlay":
            self.show(config)
        else:
            self.hide()

    def _run_tk(self):
        try:
            import tkinter as tk
        except Exception:
            return

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.resizable(False, False)
        self.root.configure(bg="#ff00ff")
        self.root.attributes("-transparentcolor", "#ff00ff")
        self.root.attributes("-topmost", True)

        self.label = tk.Label(
            self.root,
            bg="#ff00ff",
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
        )
        self.label.pack()

        self.root.update_idletasks()
        self._make_click_through()
        self.ready.set()
        self.root.mainloop()

    def _apply_pending_config(self):
        if not self.pending_config or not self.root or not self.label:
            return

        config = dict(self.pending_config)
        self._show(config)

    def _show(self, config):
        try:
            from PIL import ImageTk
        except Exception:
            self._hide()
            return

        image = self._create_overlay_image(config)
        self.photo = ImageTk.PhotoImage(image)
        self.label.configure(image=self.photo)

        work_area = self._get_work_area()
        width, height = image.size
        margin = max(32, int(config.get("watermark_overlay_margin", 32)))
        position = str(config.get("watermark_position", "bottom_right")).lower()

        left, top, right, bottom = work_area

        if position == "bottom_left":
            x = left + margin
            y = bottom - height - margin
        elif position == "top_left":
            x = left + margin
            y = top + margin
        elif position == "top_right":
            x = right - width - margin
            y = top + margin
        else:
            x = right - width - margin
            y = bottom - height - margin

        x = max(left, min(x, right - width))
        y = max(top, min(y, bottom - height))

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.deiconify()

        # Keep the fake watermark visible above the desktop layer. Without
        # topmost, Windows can keep this borderless Tk window behind the
        # wallpaper/desktop shell, especially in VirtualBox/Windows 11.
        self.root.attributes("-topmost", True)
        self.root.lift()
        self._set_topmost(bool(config.get("watermark_overlay_topmost", True)))
        self._make_click_through()
        self.is_visible = True

        # Re-apply a few times after Windows has fully shown the window. This
        # avoids a timing issue where the ex-style/topmost flags are ignored on
        # first display, especially inside a VM.
        for delay in (250, 750, 1500):
            self.root.after(
                delay,
                lambda: self._set_topmost(bool(config.get("watermark_overlay_topmost", True)))
            )

    def _hide(self):
        if self.root:
            self.root.withdraw()
        self.is_visible = False

    def _create_overlay_image(self, config):
        from PIL import Image, ImageDraw, ImageFont

        text = str(config.get("watermark_text", "ByAldon DailyWall")).strip()
        opacity = max(0.0, min(float(config.get("watermark_opacity", 0.70)), 1.0))
        scale = max(0.45, min(float(config.get("watermark_scale", 0.86)), 1.40))

        font_size = max(16, int(24 * scale))
        font = None

        for font_file in [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]:
            if Path(font_file).exists():
                font = ImageFont.truetype(font_file, font_size)
                break

        if font is None:
            font = ImageFont.load_default()

        dummy = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(dummy)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = max(1, text_bbox[2] - text_bbox[0])
        text_height = max(1, text_bbox[3] - text_bbox[1])

        icon = None
        icon_path = Path(str(config.get("watermark_icon", "")))
        if icon_path.exists():
            icon = Image.open(icon_path).convert("RGBA")
            icon_size = max(22, int(36 * scale))
            icon.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)

        icon_width = icon.width if icon else 0
        icon_height = icon.height if icon else 0

        gap = max(8, int(9 * scale)) if icon and text else 0
        padding_x = max(14, int(18 * scale))
        padding_y = max(10, int(12 * scale))

        content_width = icon_width + gap + text_width
        content_height = max(icon_height, text_height)
        width = content_width + padding_x * 2
        height = content_height + padding_y * 2

        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        box_alpha = int(150 * opacity)
        text_alpha = int(255 * opacity)
        radius = max(10, int(height * 0.28))

        draw.rounded_rectangle(
            [0, 0, width - 1, height - 1],
            radius=radius,
            fill=(0, 0, 0, box_alpha),
        )

        cursor_x = padding_x
        center_y = height // 2

        if icon:
            icon_layer = Image.new("RGBA", icon.size, (0, 0, 0, 0))
            icon_layer.alpha_composite(icon)
            alpha = icon_layer.getchannel("A").point(lambda value: int(value * opacity))
            icon_layer.putalpha(alpha)
            image.alpha_composite(icon_layer, (cursor_x, center_y - icon.height // 2))
            cursor_x += icon.width + gap

        if text:
            text_y = center_y - text_height // 2 - text_bbox[1]
            draw.text((cursor_x, text_y), text, font=font, fill=(255, 255, 255, text_alpha))

        return image

    def _get_work_area(self):
        rect = RECT()
        ok = ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)

        if ok:
            return rect.left, rect.top, rect.right, rect.bottom

        width = ctypes.windll.user32.GetSystemMetrics(0)
        height = ctypes.windll.user32.GetSystemMetrics(1)
        return 0, 0, width, height

    def _make_click_through(self):
        if not self.root:
            return

        try:
            hwnd = self.root.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception:
            pass

    def _set_topmost(self, topmost):
        if not self.root:
            return

        try:
            hwnd = self.root.winfo_id()
            insert_after = HWND_TOPMOST if topmost else HWND_NOTOPMOST
            ctypes.windll.user32.SetWindowPos(
                hwnd,
                insert_after,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
            )
        except Exception:
            pass
