import ctypes
import json
import os
import sys
import threading
import urllib.request
import webbrowser
import winreg
from pathlib import Path

import pystray
from PIL import Image

from wallpaper.app_core import APP_VERSION, load_config, run_dailywall, save_config


APP_NAME = "ByAldon DailyWall"
STARTUP_REG_NAME = "ByAldonDailyWall"
ICON_PATH = Path("assets/icon.png")
ICON_ICO_PATH = Path("assets/icon.ico")
GITHUB_URL = "https://github.com/ByAldon/ByAldon-DailyWall"
GITHUB_LATEST_RELEASE_API = "https://api.github.com/repos/ByAldon/ByAldon-DailyWall/releases/latest"
GITHUB_RELEASES_API = "https://api.github.com/repos/ByAldon/ByAldon-DailyWall/releases"

MB_OK = 0x00000000
MB_ICONINFORMATION = 0x00000040
MB_ICONERROR = 0x00000010
MB_SETFOREGROUND = 0x00010000


class DailyWallTrayApp:
    def __init__(self):
        self.icon = None
        self.is_running_job = False

    def log(self, message):
        print(message)

    def show_message_box(self, title, message, icon_type="info"):
        """
        Show a native Windows message box.

        It is shown from a separate thread so the tray menu does not get stuck.
        """

        def worker():
            flags = MB_OK | MB_SETFOREGROUND

            if icon_type == "error":
                flags |= MB_ICONERROR
            else:
                flags |= MB_ICONINFORMATION

            try:
                ctypes.windll.user32.MessageBoxW(
                    None,
                    str(message),
                    str(title),
                    flags
                )
            except Exception:
                print(f"{title}: {message}")

        threading.Thread(target=worker, daemon=True).start()

    def run_wallpaper_job(self):
        if self.is_running_job:
            return

        self.is_running_job = True

        try:
            run_dailywall(logger=self.log)
        except Exception as error:
            self.show_error("ByAldon DailyWall", f"Something went wrong:\n\n{error}")
        finally:
            self.is_running_job = False

    def run_wallpaper_job_in_background(self):
        thread = threading.Thread(target=self.run_wallpaper_job, daemon=True)
        thread.start()

    def normalize_version(self, version):
        """
        Convert versions like 'v0.6.1' or '0.6.1' to a tuple of integers.

        Examples:
            'v0.6.1' -> (0, 6, 1)
            '0.6.1'  -> (0, 6, 1)
        """

        cleaned = str(version).strip().lower()

        if cleaned.startswith("v"):
            cleaned = cleaned[1:]

        parts = []

        for part in cleaned.split("."):
            number = ""

            for character in part:
                if character.isdigit():
                    number += character
                else:
                    break

            if number:
                parts.append(int(number))
            else:
                parts.append(0)

        while len(parts) < 3:
            parts.append(0)

        return tuple(parts[:3])

    def fetch_github_json(self, url):
        """
        Fetch JSON from GitHub using only the Python standard library.
        """

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"{APP_NAME}/{APP_VERSION}",
                "Accept": "application/vnd.github+json"
            }
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            data = response.read().decode("utf-8")

        return json.loads(data)

    def get_latest_release_info(self):
        """
        Return the best available GitHub release.

        First it tries the official latest release endpoint.
        If that fails because there is no normal public release yet, it falls
        back to the releases list and includes pre-releases. This is useful
        while the project is still in early development.
        """

        try:
            release = self.fetch_github_json(GITHUB_LATEST_RELEASE_API)

            return {
                "tag_name": release.get("tag_name", "").strip(),
                "html_url": release.get("html_url", GITHUB_URL),
                "is_prerelease": bool(release.get("prerelease", False))
            }

        except Exception:
            releases = self.fetch_github_json(GITHUB_RELEASES_API)

            if not isinstance(releases, list) or not releases:
                return None

            best_release = None
            best_version = None

            for release in releases:
                tag_name = release.get("tag_name", "").strip()

                if not tag_name:
                    continue

                version = self.normalize_version(tag_name)

                if best_version is None or version > best_version:
                    best_release = release
                    best_version = version

            if not best_release:
                return None

            return {
                "tag_name": best_release.get("tag_name", "").strip(),
                "html_url": best_release.get("html_url", GITHUB_URL),
                "is_prerelease": bool(best_release.get("prerelease", False))
            }

    def check_for_updates(self):
        """
        Check GitHub Releases for the latest published version.

        During development this also supports GitHub pre-releases.
        """

        try:
            release_info = self.get_latest_release_info()

            if not release_info:
                self.show_message_box(
                    "Check for updates",
                    "No GitHub releases were found yet.\n\n"
                    "Create a release such as v0.6.0 to enable update checking.",
                    icon_type="info"
                )
                return

            latest_tag = release_info["tag_name"]
            release_url = release_info["html_url"]
            is_prerelease = release_info["is_prerelease"]

            if not latest_tag:
                self.show_message_box(
                    "Check for updates",
                    "Could not find a version tag in the GitHub release.",
                    icon_type="error"
                )
                return

            current_version = self.normalize_version(APP_VERSION)
            latest_version = self.normalize_version(latest_tag)
            release_type = "pre-release" if is_prerelease else "release"

            if latest_version > current_version:
                self.show_update_available(latest_tag, release_url, release_type)
            else:
                self.show_message_box(
                    "Check for updates",
                    f"You are up to date.\n\n"
                    f"Current version: {APP_VERSION}\n"
                    f"Latest {release_type}: {latest_tag}",
                    icon_type="info"
                )

        except Exception as error:
            self.show_message_box(
                "Check for updates",
                "Could not check for updates.\n\n"
                "Make sure you are connected to the internet and that the GitHub repository is reachable.\n\n"
                f"Details:\n{error}",
                icon_type="error"
            )

    def show_update_available(self, latest_tag, release_url, release_type="release"):
        """
        Show a small update-available window with a button to open GitHub.
        """

        def worker():
            try:
                import tkinter as tk
            except Exception:
                self.show_message_box(
                    "Update available",
                    f"A new {release_type} is available.\n\n"
                    f"Current version: {APP_VERSION}\n"
                    f"Latest version: {latest_tag}\n\n"
                    f"Download it here:\n{release_url}",
                    icon_type="info"
                )
                return

            window = tk.Tk()
            self.set_window_icon(window)
            window.title("Update available")
            window.resizable(False, False)
            window.geometry("470x230")
            window.attributes("-topmost", True)
            window.lift()
            window.focus_force()

            frame = tk.Frame(window, padx=24, pady=22)
            frame.pack(fill="both", expand=True)

            title = tk.Label(
                frame,
                text="Update available",
                font=("Segoe UI", 14, "bold")
            )
            title.pack(anchor="w")

            message = tk.Label(
                frame,
                text=(
                    f"A newer {release_type} of {APP_NAME} is available.\n\n"
                    f"Current version: {APP_VERSION}\n"
                    f"Latest version: {latest_tag}"
                ),
                wraplength=440,
                justify="left",
                fg="#444444"
            )
            message.pack(anchor="w", fill="x", pady=(8, 14))

            button_frame = tk.Frame(frame)
            button_frame.pack(anchor="e", fill="x", pady=(8, 0))

            def open_release():
                webbrowser.open(release_url)

            open_button = tk.Button(
                button_frame,
                text="Open latest release",
                width=18,
                command=open_release
            )
            open_button.pack(side="right")

            close_button = tk.Button(
                button_frame,
                text="Close",
                width=12,
                command=window.destroy
            )
            close_button.pack(side="right", padx=(0, 8))

            window.protocol("WM_DELETE_WINDOW", window.destroy)
            window.mainloop()

        threading.Thread(target=worker, daemon=True).start()

    def show_about(self, icon=None, item=None):
        """
        Open a small About window with version information and a GitHub link.
        """

        threading.Thread(target=self._open_about_window, daemon=True).start()

    def _open_about_window(self):
        try:
            import tkinter as tk
        except Exception:
            self.show_message_box(
                "About ByAldon DailyWall",
                f"{APP_NAME}\n"
                f"Version: {APP_VERSION}\n\n"
                f"GitHub:\n{GITHUB_URL}",
                icon_type="info"
            )
            return

        window = tk.Tk()
        self.set_window_icon(window)
        window.title("About ByAldon DailyWall")
        window.resizable(False, False)
        window.geometry("500x340")
        window.attributes("-topmost", True)
        window.lift()
        window.focus_force()

        frame = tk.Frame(window, padx=24, pady=22)
        frame.pack(fill="both", expand=True)

        title = tk.Label(
            frame,
            text=APP_NAME,
            font=("Segoe UI", 15, "bold")
        )
        title.pack(anchor="w")

        version = tk.Label(
            frame,
            text=f"Version: {APP_VERSION}",
            font=("Segoe UI", 10)
        )
        version.pack(anchor="w", pady=(4, 14))

        description = tk.Label(
            frame,
            text=(
                "A lightweight Windows wallpaper changer.\n\n"
                "Independent project. Not affiliated with, endorsed by, "
                "or sponsored by Microsoft or Bing."
            ),
            wraplength=440,
            justify="left",
            fg="#444444"
        )
        description.pack(anchor="w", fill="x")

        repo_label = tk.Label(
            frame,
            text="GitHub repository:",
            font=("Segoe UI", 10, "bold")
        )
        repo_label.pack(anchor="w", pady=(16, 2))

        repo_link = tk.Label(
            frame,
            text=GITHUB_URL,
            fg="#0066cc",
            cursor="hand2",
            wraplength=440,
            justify="left"
        )
        repo_link.pack(anchor="w")

        def open_repo(event=None):
            webbrowser.open(GITHUB_URL)

        repo_link.bind("<Button-1>", open_repo)

        button_frame = tk.Frame(frame)
        button_frame.pack(anchor="e", fill="x", pady=(22, 0))

        open_button = tk.Button(
            button_frame,
            text="Open GitHub repository",
            width=22,
            command=open_repo
        )
        open_button.pack(side="right")

        update_button = tk.Button(
            button_frame,
            text="Check for updates",
            width=18,
            command=self.check_for_updates
        )
        update_button.pack(side="right", padx=(0, 8))

        close_button = tk.Button(
            button_frame,
            text="Close",
            width=12,
            command=window.destroy
        )
        close_button.pack(side="right", padx=(0, 8))

        window.protocol("WM_DELETE_WINDOW", window.destroy)
        window.mainloop()

    def show_error(self, title, message):
        self.show_message_box(title, message, icon_type="error")

    def set_window_icon(self, window):
        """
        Set the ByAldon icon on Tkinter windows.

        This fixes the default Tkinter feather icon in windows like
        About and Settings.
        """

        try:
            if ICON_ICO_PATH.exists():
                window.iconbitmap(str(ICON_ICO_PATH))
        except Exception:
            pass

    def get_startup_command(self):
        """
        Build the command Windows should run at user login.

        In development mode this starts tray.py with the current Python executable.
        In a packaged EXE later, it will run the EXE directly.
        """

        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'

        tray_path = Path(__file__).resolve()
        python_exe = Path(sys.executable).resolve()

        return f'"{python_exe}" "{tray_path}"'

    def is_startup_enabled(self):
        """
        Check if ByAldon DailyWall is registered to start with Windows.
        """

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            ) as key:
                winreg.QueryValueEx(key, STARTUP_REG_NAME)
                return True
        except FileNotFoundError:
            return False
        except OSError:
            return False

    def set_startup_enabled(self, enabled):
        """
        Enable or disable startup with Windows for the current user.
        """

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(
                    key,
                    STARTUP_REG_NAME,
                    0,
                    winreg.REG_SZ,
                    self.get_startup_command()
                )
            else:
                try:
                    winreg.DeleteValue(key, STARTUP_REG_NAME)
                except FileNotFoundError:
                    pass

    def open_settings(self, icon=None, item=None):
        """
        Open settings in a separate thread.

        This prevents the pystray menu callback from being blocked by Tkinter.
        """

        threading.Thread(target=self._open_settings_window, daemon=True).start()

    def _open_settings_window(self):
        try:
            import tkinter as tk
            from tkinter import messagebox
        except Exception as error:
            self.show_error("Settings", f"Could not open settings:\n\n{error}")
            return

        try:
            config = load_config()
        except Exception as error:
            self.show_error("Settings", f"Could not load config.json:\n\n{error}")
            return

        window = tk.Tk()
        self.set_window_icon(window)
        window.title("ByAldon DailyWall Settings")
        window.resizable(False, False)
        window.geometry("720x690")
        window.attributes("-topmost", True)
        window.lift()
        window.focus_force()

        apply_watermark_var = tk.BooleanVar(value=bool(config.get("apply_watermark", True)))
        set_as_wallpaper_var = tk.BooleanVar(value=bool(config.get("set_as_wallpaper", True)))
        start_with_windows_var = tk.BooleanVar(value=self.is_startup_enabled())
        mode_var = tk.StringVar(value=config.get("set_wallpaper_mode", "new_only"))

        frame = tk.Frame(window, padx=28, pady=22)
        frame.pack(fill="both", expand=True)

        title = tk.Label(
            frame,
            text="ByAldon DailyWall Settings",
            font=("Segoe UI", 14, "bold")
        )
        title.pack(anchor="w")

        intro = tk.Label(
            frame,
            text=(
                "Choose how ByAldon DailyWall starts, saves, and applies your daily wallpaper. "
                "These settings are stored locally on your computer."
            ),
            wraplength=650,
            justify="left",
            anchor="w",
            fg="#444444"
        )
        intro.pack(anchor="w", fill="x", pady=(8, 18))

        app_frame = tk.LabelFrame(
            frame,
            text="App startup",
            padx=16,
            pady=12,
            font=("Segoe UI", 10, "bold")
        )
        app_frame.pack(anchor="w", fill="x")

        startup_check = tk.Checkbutton(
            app_frame,
            text="Start ByAldon DailyWall when Windows starts",
            variable=start_with_windows_var,
            font=("Segoe UI", 10, "bold")
        )
        startup_check.pack(anchor="w")

        startup_help = tk.Label(
            app_frame,
            text=(
                "When enabled, ByAldon DailyWall starts automatically after you sign in to Windows. "
                "This is optional and can be turned off again here."
            ),
            wraplength=625,
            justify="left",
            anchor="w",
            fg="#555555"
        )
        startup_help.pack(anchor="w", fill="x", padx=(24, 0), pady=(2, 4))

        options_frame = tk.LabelFrame(
            frame,
            text="Wallpaper options",
            padx=16,
            pady=12,
            font=("Segoe UI", 10, "bold")
        )
        options_frame.pack(anchor="w", fill="x", pady=(16, 0))

        watermark_check = tk.Checkbutton(
            options_frame,
            text="Show ByAldon DailyWall watermark",
            variable=apply_watermark_var,
            font=("Segoe UI", 10, "bold")
        )
        watermark_check.pack(anchor="w")

        watermark_help = tk.Label(
            options_frame,
            text=(
                "Adds your own small ByAldon DailyWall branding to a separate local copy. "
                "The original downloaded wallpaper is kept untouched."
            ),
            wraplength=625,
            justify="left",
            anchor="w",
            fg="#555555"
        )
        watermark_help.pack(anchor="w", fill="x", padx=(24, 0), pady=(2, 12))

        wallpaper_check = tk.Checkbutton(
            options_frame,
            text="Set image as Windows wallpaper",
            variable=set_as_wallpaper_var,
            font=("Segoe UI", 10, "bold")
        )
        wallpaper_check.pack(anchor="w")

        wallpaper_help = tk.Label(
            options_frame,
            text=(
                "When enabled, the app applies the downloaded or watermarked image as your desktop background. "
                "Turn this off if you only want to download the image."
            ),
            wraplength=625,
            justify="left",
            anchor="w",
            fg="#555555"
        )
        wallpaper_help.pack(anchor="w", fill="x", padx=(24, 0), pady=(2, 6))

        mode_frame = tk.LabelFrame(
            frame,
            text="Update behavior",
            padx=16,
            pady=12,
            font=("Segoe UI", 10, "bold")
        )
        mode_frame.pack(anchor="w", fill="x", pady=(16, 0))

        mode_row = tk.Frame(mode_frame)
        mode_row.pack(anchor="w", fill="x")

        mode_label = tk.Label(
            mode_row,
            text="Wallpaper mode:",
            font=("Segoe UI", 10, "bold")
        )
        mode_label.pack(side="left")

        mode_menu = tk.OptionMenu(mode_row, mode_var, "new_only", "always")
        mode_menu.config(width=12)
        mode_menu.pack(side="left", padx=(10, 0))

        mode_help = tk.Label(
            mode_frame,
            text=(
                "new_only: update the desktop only when a new wallpaper or new watermarked copy is created.\n"
                "always: apply the current local wallpaper every time the app runs."
            ),
            wraplength=625,
            justify="left",
            anchor="w",
            fg="#555555"
        )
        mode_help.pack(anchor="w", fill="x", padx=(24, 0), pady=(8, 0))

        note = tk.Label(
            frame,
            text=(
                "Tip: If you switch the watermark on or off, use 'Save and run now' "
                "to apply the change immediately."
            ),
            wraplength=650,
            justify="left",
            anchor="w",
            fg="#666666"
        )
        note.pack(anchor="w", fill="x", pady=(18, 18))

        separator = tk.Frame(frame, height=1, bg="#d0d0d0")
        separator.pack(fill="x", pady=(0, 14))

        button_frame = tk.Frame(frame)
        button_frame.pack(anchor="e", fill="x")

        def save_settings(show_confirmation=True):
            config["apply_watermark"] = bool(apply_watermark_var.get())
            config["set_as_wallpaper"] = bool(set_as_wallpaper_var.get())
            config["set_wallpaper_mode"] = mode_var.get()

            try:
                save_config(config)
                self.set_startup_enabled(bool(start_with_windows_var.get()))

                if show_confirmation:
                    messagebox.showinfo(
                        "Settings saved",
                        "Your settings have been saved."
                    )

                return True

            except Exception as error:
                messagebox.showerror(
                    "Settings",
                    f"Could not save settings:\n\n{error}"
                )
                return False

        def save_and_run():
            if save_settings(show_confirmation=False):
                self.run_wallpaper_job_in_background()
                messagebox.showinfo(
                    "Settings saved",
                    "Your settings have been saved.\n\nByAldon DailyWall is now applying them."
                )

        close_button = tk.Button(button_frame, text="Close", width=14, command=window.destroy)
        close_button.pack(side="right")

        save_button = tk.Button(button_frame, text="Save", width=14, command=save_settings)
        save_button.pack(side="right", padx=(0, 8))

        save_run_button = tk.Button(
            button_frame,
            text="Save and run now",
            width=20,
            command=save_and_run
        )
        save_run_button.pack(side="right", padx=(0, 8))

        window.protocol("WM_DELETE_WINDOW", window.destroy)
        window.mainloop()

    def close_app(self, icon=None, item=None):
        """
        Close the tray app.

        pystray can sometimes keep a Windows event loop alive, especially during
        development. Stop the tray icon first, then force-exit as a reliable
        fallback.
        """

        try:
            if self.icon:
                self.icon.visible = False
                self.icon.stop()
        finally:
            os._exit(0)

    def create_icon_image(self):
        if ICON_PATH.exists():
            return Image.open(ICON_PATH).convert("RGBA")

        return Image.new("RGBA", (64, 64), (0, 128, 255, 255))

    def run(self):
        image = self.create_icon_image()

        menu = pystray.Menu(
            pystray.MenuItem("About", self.show_about),
            pystray.MenuItem("Settings", self.open_settings),
            pystray.MenuItem("Close app", self.close_app)
        )

        self.icon = pystray.Icon(
            "ByAldon DailyWall",
            image,
            "ByAldon DailyWall",
            menu
        )

        self.run_wallpaper_job_in_background()
        self.icon.run()


def main():
    app = DailyWallTrayApp()
    app.run()


if __name__ == "__main__":
    main()
