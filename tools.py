import ctypes
from datetime import datetime
import os
import re
import shutil
import subprocess
from urllib.parse import quote_plus
import webbrowser

from PIL import ImageGrab
import psutil


SCREENSHOT_DIR = r"D:\Jarvis\screenshots"

_APP_REGISTRY: dict[str, dict[str, list[str] | str]] = {
    "notepad": {"launch": "notepad.exe", "processes": ["notepad.exe"]},
    "calculator": {"launch": "calc.exe", "processes": ["CalculatorApp.exe", "calc.exe"]},
    "chrome": {"launch": "chrome", "processes": ["chrome.exe"]},
    "vscode": {"launch": "code", "processes": ["Code.exe"]},
    "xampp": {"launch": r"C:\xampp\xampp-control.exe", "processes": ["xampp-control.exe"]},
    "cmd": {"launch": "cmd.exe", "processes": ["cmd.exe"]},
    "task manager": {"launch": "taskmgr.exe", "processes": ["Taskmgr.exe"]},
}

_APP_ALIASES: dict[str, str] = {
    "calc": "calculator",
    "google chrome": "chrome",
    "browser": "chrome",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "code": "vscode",
    "xampp control": "xampp",
    "xampp control panel": "xampp",
    "command prompt": "cmd",
    "terminal": "cmd",
    "taskmgr": "task manager",
}


def get_system_stats() -> str:
    """Retrieve live Windows CPU usage, RAM consumption, and battery percentage.

    Returns:
        str: Live telemetry summary of CPU, RAM, and battery status.
    """
    cpu_percent = psutil.cpu_percent(interval=0.3)

    mem = psutil.virtual_memory()
    used_gb = mem.used / (1024 ** 3)
    total_gb = mem.total / (1024 ** 3)
    ram_percent = mem.percent

    battery = psutil.sensors_battery()
    if battery is not None:
        plug_state = "charging" if battery.power_plugged else "on battery"
        battery_info = f"Battery is at {battery.percent:.0f}% ({plug_state})."
    else:
        battery_info = "Battery telemetry unavailable (running on AC power)."

    return (
        f"CPU load is {cpu_percent:.1f}%. "
        f"RAM usage is {used_gb:.2f} GB out of {total_gb:.2f} GB ({ram_percent:.0f}%). "
        f"{battery_info}"
    )


def control_windows_app(action: str, app_name: str) -> str:
    """Open or close supported Windows desktop applications.

    Args:
        action (str): Either "open" or "close".
        app_name (str): Supported app name ("notepad", "calculator", "chrome",
            "vscode", "xampp", "cmd", or "task manager").

    Returns:
        str: Confirmation message indicating the action result.
    """
    normalized_action = action.strip().lower()
    raw_app = app_name.strip().lower()
    canonical_app = _APP_ALIASES.get(raw_app, raw_app)

    if canonical_app not in _APP_REGISTRY:
        supported = ", ".join(_APP_REGISTRY.keys())
        return f"Unsupported application '{app_name}'. Supported apps are: {supported}."

    app_info = _APP_REGISTRY[canonical_app]

    if normalized_action in {"open", "start", "launch", "run"}:
        try:
            if canonical_app == "cmd":
                subprocess.Popen(["cmd.exe"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif canonical_app == "xampp":
                xampp_paths = [r"C:\xampp\xampp-control.exe", r"D:\xampp\xampp-control.exe"]
                found_path = next((p for p in xampp_paths if os.path.exists(p)), None)
                if not found_path:
                    return "Could not find xampp-control.exe in C:\\xampp or D:\\xampp."
                os.startfile(found_path)
            elif canonical_app == "vscode":
                code_bin = shutil.which("code")
                if code_bin:
                    subprocess.Popen([code_bin], creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    os.startfile("code")
            else:
                launch_target = str(app_info["launch"])
                subprocess.Popen(
                    ["cmd", "/c", "start", "", launch_target],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            return f"Opened {canonical_app}."
        except Exception as exc:
            return f"Failed to open {canonical_app}: {exc}"

    if normalized_action in {"close", "exit", "kill", "stop", "quit"}:
        processes: list[str] = list(app_info["processes"])
        terminated_any = False

        for proc_name in processes:
            result = subprocess.run(
                ["taskkill", "/f", "/im", proc_name],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                terminated_any = True

        if terminated_any:
            return f"Closed {canonical_app}."
        return f"{canonical_app} does not appear to be running."

    return f"Invalid action '{action}'. Use 'open' or 'close'."


def web_search_or_open(query_or_url: str, platform: str = "google") -> str:
    """Open a direct URL or search Google, YouTube, or GitHub in the default browser.

    Args:
        query_or_url (str): A URL/domain or a search query string.
        platform (str): Search platform ("google", "youtube", or "github").

    Returns:
        str: Confirmation of the opened URL or search query.
    """
    target = query_or_url.strip()
    if not target:
        return "No URL or search query was provided."

    is_direct_url = target.startswith(("http://", "https://")) or (
        " " not in target and bool(re.match(r"^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(/.*)?$", target))
    )

    if is_direct_url:
        url = target if target.startswith(("http://", "https://")) else f"https://{target}"
        webbrowser.open(url)
        return f"Opened {url} in your browser."

    encoded_query = quote_plus(target)
    selected_platform = platform.strip().lower()

    if selected_platform == "youtube":
        search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        label = "YouTube"
    elif selected_platform == "github":
        search_url = f"https://github.com/search?q={encoded_query}"
        label = "GitHub"
    else:
        search_url = f"https://www.google.com/search?q={encoded_query}"
        label = "Google"

    webbrowser.open(search_url)
    return f"Searched {label} for '{target}'."


def system_power_control(command: str) -> str:
    """Lock the Windows workstation, mute/unmute system audio, or take a screenshot.

    Args:
        command (str): One of "lock", "mute", "unmute", or "screenshot".

    Returns:
        str: Status message confirming the executed system action.
    """
    cmd = command.strip().lower()

    if "lock" in cmd:
        ctypes.windll.user32.LockWorkStation()
        return "Windows workstation locked."

    if "mute" in cmd:
        VK_VOLUME_MUTE = 0xAD
        KEYEVENTF_KEYUP = 0x0002
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, 0)
        return "Toggled system audio mute."

    if "screenshot" in cmd or "capture" in cmd or "screen" in cmd:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(SCREENSHOT_DIR, f"jarvis_{timestamp}.png")

        screenshot = ImageGrab.grab(all_screens=True)
        screenshot.save(file_path, format="PNG")
        return f"Screenshot saved to {file_path}."

    return f"Unrecognized command '{command}'. Use 'lock', 'mute', 'unmute', or 'screenshot'."


def read_clipboard() -> str:
    """Read text or code currently copied to the Windows clipboard.

    Returns:
        str: Text content stored in the clipboard.
    """
    CF_UNICODETEXT = 13
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_bool
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_bool

    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_bool

    if not user32.OpenClipboard(None):
        return "Unable to access the Windows clipboard right now."

    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return "The clipboard is currently empty or contains non-text data."

        locked_ptr = kernel32.GlobalLock(handle)
        if not locked_ptr:
            return "Failed to read clipboard memory buffer."

        try:
            text = ctypes.wstring_at(locked_ptr)
        finally:
            kernel32.GlobalUnlock(handle)

        cleaned = text.strip()
        if not cleaned:
            return "The clipboard contains only whitespace."

        if len(cleaned) > 12000:
            cleaned = cleaned[:12000] + "\n...[truncated due to length]"

        return cleaned
    finally:
        user32.CloseClipboard()