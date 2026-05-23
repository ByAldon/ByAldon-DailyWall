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

from wallpaper.overlay import WatermarkOverlay

from wallpaper.app_core import APP_VERSION, create_default_config, get_user_data_path, load_config, load_runtime_config, resolve_config_path, resource_path, run_dailywall, save_config


APP_NAME = "ByAldon DailyWall"
STARTUP_REG_NAME = "ByAldonDailyWall"
ICON_PATH = resource_path("assets/icon.png")
ICON_ICO_PATH = resource_path("assets/icon.ico")
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
        self.watermark_overlay = WatermarkOverlay()

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

    def run_wallpaper_job(self, force_apply=False):
        if self.is_running_job:
            return

        self.is_running_job = True

        try:
            run_dailywall(logger=self.log, force_apply=force_apply)
            self.sync_watermark_overlay()
        except Exception as error:
            self.show_error("ByAldon DailyWall", f"Something went wrong:\n\n{error}")
        finally:
            self.is_running_job = False

    def run_wallpaper_job_in_background(self, force_apply=False):
        thread = threading.Thread(
            target=self.run_wallpaper_job,
            kwargs={"force_apply": force_apply},
            daemon=True
        )
        thread.start()

    def sync_watermark_overlay(self):
        """Show or hide the fake desktop watermark based on current settings."""

        try:
            config = load_runtime_config()
            self.watermark_overlay.refresh(config)
        except Exception as error:
            print(f"Could not refresh watermark overlay: {error}")

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
            self.show_error("Settings", f"Could not load settings:\n\n{error}")
            return

        config_file_path = resolve_config_path()
        settings_folder = get_user_data_path()

        window = tk.Tk()
        self.set_window_icon(window)
        window.title("ByAldon DailyWall Settings")
        window.resizable(True, True)
        window.geometry("850x650")
        window.minsize(620, 480)
        window.attributes("-topmost", True)
        window.lift()
        window.focus_force()

        current_mode = str(config.get("set_wallpaper_mode", "always")).lower()
        if current_mode not in ("new_only", "always"):
            current_mode = "always"

        current_watermark_mode = str(config.get("watermark_mode", "burned_in")).lower()
        if current_watermark_mode not in ("burned_in", "overlay"):
            current_watermark_mode = "burned_in"

        apply_watermark_var = tk.BooleanVar(value=bool(config.get("apply_watermark", True)))
        set_as_wallpaper_var = tk.BooleanVar(value=bool(config.get("set_as_wallpaper", True)))
        start_with_windows_var = tk.BooleanVar(value=self.is_startup_enabled())
        mode_var = tk.StringVar(value=current_mode)
        watermark_mode_var = tk.StringVar(value=current_watermark_mode)

        outer = tk.Frame(window)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)

        scroll_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def update_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_scroll_width(event):
            canvas.itemconfigure(scroll_window, width=event.width)

        scroll_frame.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_scroll_width)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def on_mousewheel(event):
            # Windows/macOS mousewheel support.
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_mousewheel_linux_up(event):
            canvas.yview_scroll(-1, "units")

        def on_mousewheel_linux_down(event):
            canvas.yview_scroll(1, "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)
        canvas.bind_all("<Button-4>", on_mousewheel_linux_up)
        canvas.bind_all("<Button-5>", on_mousewheel_linux_down)

        frame = tk.Frame(scroll_frame, padx=24, pady=18)
        frame.pack(fill="both", expand=True)

        title = tk.Label(frame, text="ByAldon DailyWall Settings", font=("Segoe UI", 14, "bold"))
        title.pack(anchor="w")

        intro = tk.Label(
            frame,
            text=("Choose how ByAldon DailyWall starts, saves, and applies your wallpaper. "
                  "Your choices are saved in AppData, not beside the EXE."),
            wraplength=760,
            justify="left",
            anchor="w",
            fg="#444444"
        )
        intro.pack(anchor="w", fill="x", pady=(6, 10))

        data_frame = tk.LabelFrame(frame, text="Settings location", padx=14, pady=8, font=("Segoe UI", 10, "bold"))
        data_frame.pack(anchor="w", fill="x")

        tk.Label(
            data_frame,
            text=f"Config file: {config_file_path}",
            wraplength=760,
            justify="left",
            anchor="w",
            fg="#333333"
        ).pack(anchor="w", fill="x")

        def open_settings_folder():
            try:
                os.startfile(settings_folder)
            except Exception as error:
                messagebox.showerror("Open settings folder", f"Could not open the settings folder:\n\n{error}")

        tk.Button(data_frame, text="Open settings folder", width=20, command=open_settings_folder).pack(anchor="w", pady=(6, 0))

        app_frame = tk.LabelFrame(frame, text="App startup", padx=14, pady=8, font=("Segoe UI", 10, "bold"))
        app_frame.pack(anchor="w", fill="x", pady=(8, 0))

        tk.Checkbutton(
            app_frame,
            text="Start ByAldon DailyWall when Windows starts",
            variable=start_with_windows_var,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        tk.Label(
            app_frame,
            text="Starts the app automatically after you sign in to Windows. You can turn this off again here.",
            wraplength=760,
            justify="left",
            anchor="w",
            fg="#555555"
        ).pack(anchor="w", fill="x", padx=(24, 0), pady=(2, 0))

        options_frame = tk.LabelFrame(frame, text="Wallpaper options", padx=14, pady=8, font=("Segoe UI", 10, "bold"))
        options_frame.pack(anchor="w", fill="x", pady=(8, 0))

        tk.Checkbutton(
            options_frame,
            text="Show ByAldon DailyWall watermark",
            variable=apply_watermark_var,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        tk.Label(
            options_frame,
            text="Shows small ByAldon DailyWall branding. The original downloaded wallpaper stays untouched.",
            wraplength=760,
            justify="left",
            anchor="w",
            fg="#555555"
        ).pack(anchor="w", fill="x", padx=(24, 0), pady=(2, 6))

        tk.Checkbutton(
            options_frame,
            text="Set image as Windows wallpaper",
            variable=set_as_wallpaper_var,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        tk.Label(
            options_frame,
            text="Applies the downloaded or watermarked image as your desktop background. Turn this off to only download images.",
            wraplength=760,
            justify="left",
            anchor="w",
            fg="#555555"
        ).pack(anchor="w", fill="x", padx=(24, 0), pady=(2, 0))

        watermark_style_frame = tk.LabelFrame(
            frame,
            text="Watermark style",
            padx=14,
            pady=8,
            font=("Segoe UI", 10, "bold")
        )
        watermark_style_frame.pack(anchor="w", fill="x", pady=(8, 0))

        tk.Radiobutton(
            watermark_style_frame,
            text="Reliable: create a local watermarked wallpaper copy",
            variable=watermark_mode_var,
            value="burned_in"
        ).pack(anchor="w", padx=(18, 0))

        tk.Radiobutton(
            watermark_style_frame,
            text="Experimental: show watermark as a desktop overlay",
            variable=watermark_mode_var,
            value="overlay"
        ).pack(anchor="w", padx=(18, 0))

        tk.Label(
            watermark_style_frame,
            text=("Recommended: use the reliable local copy. It is visible on normal Windows and in VMs. "
                  "The original wallpaper is still kept untouched. The watermark is placed in the top-right corner by default, with extra spacing from the screen edges."),
            wraplength=760,
            justify="left",
            anchor="w",
            fg="#555555"
        ).pack(anchor="w", fill="x", padx=(18, 0), pady=(4, 0))

        mode_frame = tk.LabelFrame(frame, text="Update behavior", padx=14, pady=8, font=("Segoe UI", 10, "bold"))
        mode_frame.pack(anchor="w", fill="x", pady=(8, 0))

        tk.Label(mode_frame, text="Wallpaper mode:", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        tk.Radiobutton(
            mode_frame,
            text="Update only when a new wallpaper is downloaded",
            variable=mode_var,
            value="new_only"
        ).pack(anchor="w", padx=(18, 0), pady=(2, 0))

        tk.Radiobutton(
            mode_frame,
            text="Apply the current local wallpaper every time the app runs",
            variable=mode_var,
            value="always"
        ).pack(anchor="w", padx=(18, 0))

        tk.Label(
            mode_frame,
            text="Use 'always' if you want Settings changes, such as watermark on/off, to be applied more predictably.",
            wraplength=760,
            justify="left",
            anchor="w",
            fg="#555555"
        ).pack(anchor="w", fill="x", padx=(18, 0), pady=(3, 0))

        tk.Label(
            frame,
            text="Tip: after changing the watermark setting, click 'Save and run now' to apply it immediately.",
            wraplength=760,
            justify="left",
            anchor="w",
            fg="#666666"
        ).pack(anchor="w", fill="x", pady=(8, 10))

        # Fixed button bar. This stays visible even when the settings content scrolls.
        button_bar = tk.Frame(window, padx=14, pady=10, relief="groove", borderwidth=1)
        button_bar.pack(side="bottom", fill="x")

        def save_settings(show_confirmation=True):
            config["apply_watermark"] = bool(apply_watermark_var.get())
            config["set_as_wallpaper"] = bool(set_as_wallpaper_var.get())
            config["set_wallpaper_mode"] = mode_var.get()
            config["watermark_mode"] = watermark_mode_var.get()
            config["watermark_overlay_topmost"] = True

            try:
                save_config(config)
                self.set_startup_enabled(bool(start_with_windows_var.get()))

                saved_config = load_config()

                apply_watermark_var.set(bool(saved_config.get("apply_watermark", True)))
                set_as_wallpaper_var.set(bool(saved_config.get("set_as_wallpaper", True)))
                mode_var.set(str(saved_config.get("set_wallpaper_mode", "always")))
                watermark_mode_var.set(str(saved_config.get("watermark_mode", "burned_in")))

                self.sync_watermark_overlay()

                if show_confirmation:
                    messagebox.showinfo(
                        "Settings saved",
                        "Your settings have been saved.\n\n"
                        f"Watermark: {'On' if saved_config.get('apply_watermark', True) else 'Off'}\n"
                        f"Watermark style: {saved_config.get('watermark_mode', 'burned_in')}\n"
                        f"Set as wallpaper: {'On' if saved_config.get('set_as_wallpaper', True) else 'Off'}\n"
                        f"Wallpaper mode: {saved_config.get('set_wallpaper_mode', 'always')}\n\n"
                        f"Saved to:\n{config_file_path}"
                    )

                return True

            except Exception as error:
                messagebox.showerror("Settings", f"Could not save settings:\n\n{error}")
                return False

        def save_and_run():
            if save_settings(show_confirmation=False):
                self.run_wallpaper_job_in_background(force_apply=True)
                messagebox.showinfo(
                    "Settings saved",
                    f"Your settings have been saved and are now being applied.\n\nSaved to:\n{config_file_path}"
                )

        def restore_defaults():
            if not messagebox.askyesno(
                "Restore defaults",
                "Restore the default settings?\n\nThis will turn the watermark on again and use the reliable local watermarked copy."
            ):
                return

            default_config = create_default_config()
            default_config["watermark_mode"] = "burned_in"

            config.clear()
            config.update(default_config)

            apply_watermark_var.set(bool(config.get("apply_watermark", True)))
            set_as_wallpaper_var.set(bool(config.get("set_as_wallpaper", True)))
            mode_var.set(config.get("set_wallpaper_mode", "always"))
            watermark_mode_var.set(config.get("watermark_mode", "burned_in"))

            if save_settings(show_confirmation=False):
                self.run_wallpaper_job_in_background(force_apply=True)
                messagebox.showinfo(
                    "Defaults restored",
                    f"Default settings were restored and are now being applied.\n\nSaved to:\n{config_file_path}"
                )

        def show_watermark_now():
            apply_watermark_var.set(True)
            set_as_wallpaper_var.set(True)
            mode_var.set("always")
            watermark_mode_var.set("burned_in")

            if save_settings(show_confirmation=False):
                self.run_wallpaper_job_in_background(force_apply=True)
                messagebox.showinfo(
                    "Watermark enabled",
                    f"The reliable watermarked copy mode has been enabled and is now being applied.\n\nSaved to:\n{config_file_path}"
                )

        tk.Button(button_bar, text="Close", width=10, command=window.destroy).pack(side="right")
        tk.Button(button_bar, text="Save", width=10, command=save_settings).pack(side="right", padx=(0, 8))
        tk.Button(button_bar, text="Save and run now", width=16, command=save_and_run).pack(side="right", padx=(0, 8))
        tk.Button(button_bar, text="Show watermark now", width=18, command=show_watermark_now).pack(side="right", padx=(0, 8))
        tk.Button(button_bar, text="Restore defaults", width=14, command=restore_defaults).pack(side="right", padx=(0, 8))

        def cleanup_bindings():
            try:
                canvas.unbind_all("<MouseWheel>")
                canvas.unbind_all("<Button-4>")
                canvas.unbind_all("<Button-5>")
            except Exception:
                pass
            window.destroy()

        window.protocol("WM_DELETE_WINDOW", cleanup_bindings)
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

        self.sync_watermark_overlay()
        self.run_wallpaper_job_in_background()
        self.icon.run()


def main():
    app = DailyWallTrayApp()
    app.run()


if __name__ == "__main__":
    main()
