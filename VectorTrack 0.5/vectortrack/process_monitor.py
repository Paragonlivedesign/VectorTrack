"""
Process monitoring module for tracking Vectorworks application status.
"""

import win32gui
import win32process
import win32con
from typing import Optional, Tuple, List, Dict
import os
from dataclasses import dataclass
try:
    import psutil
except Exception:  # pragma: no cover - fallback for lean test/runtime envs
    import sys
    import types

    class _PsutilFallbackError(Exception):
        pass

    class _PsutilFallback:
        NoSuchProcess = _PsutilFallbackError
        AccessDenied = _PsutilFallbackError

        class Process:  # noqa: D401 - compatibility shim
            def __init__(self, _pid: int):
                raise _PsutilFallbackError("psutil is required for live process lookup")

    shim = types.ModuleType("psutil")
    shim.NoSuchProcess = _PsutilFallbackError
    shim.AccessDenied = _PsutilFallbackError
    shim.Process = _PsutilFallback.Process
    sys.modules.setdefault("psutil", shim)
    psutil = shim  # type: ignore[assignment]
from loguru import logger

@dataclass
class WindowInfo:
    hwnd: int
    title: str
    process_id: int
    file_path: Optional[str] = None
    is_visible: bool = False
    is_active: bool = False
    monitor: Optional[int] = None

class ProcessMonitor:
    def __init__(self):
        self.vectorworks_windows: List[WindowInfo] = []
        self.vectorworks_path: Optional[str] = None
        self.process_name: Optional[str] = None
        self._known_paths: Dict[str, str] = {}
        self._last_file_paths: set[str] = set()
        self._closed_files: List[str] = []
        self._render_grace_tokens = (
            "render",
            "publishing",
            "export",
            "processing",
        )

    @staticmethod
    def _is_valid_hwnd(hwnd: int) -> bool:
        try:
            return bool(hwnd) and win32gui.IsWindow(hwnd)
        except Exception:
            return False
        
    def find_vectorworks_installations(self) -> Dict[str, str]:
        """Find installed Vectorworks versions."""
        program_files = [
            os.environ.get('ProgramFiles', 'C:\\Program Files'),
            os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
        ]
        
        installations = {}
        
        for program_dir in program_files:
            # Check common Vectorworks installation paths
            vw_dirs = [
                os.path.join(program_dir, "Vectorworks"),
                os.path.join(program_dir, "Nemetschek", "Vectorworks"),
            ]
            
            for vw_dir in vw_dirs:
                if os.path.exists(vw_dir):
                    for year in range(2020, 2031):  # Reasonable year range
                        year_dir = os.path.join(vw_dir, str(year))
                        exe_path = os.path.join(year_dir, "Vectorworks.exe")
                        if os.path.exists(exe_path):
                            installations[f"Vectorworks {year}"] = exe_path
                            logger.info(f"Found Vectorworks {year} at {exe_path}")
        
        self._known_paths = installations
        return installations
        
    def auto_select_vectorworks(self) -> Optional[str]:
        """Automatically select the most recent Vectorworks installation."""
        if not self._known_paths:
            self.find_vectorworks_installations()
            
        if self._known_paths:
            # Get the most recent version
            latest_version = max(self._known_paths.keys())
            exe_path = self._known_paths[latest_version]
            self.set_vectorworks_path(exe_path)
            logger.info(f"Auto-selected {latest_version} at {exe_path}")
            return exe_path
            
        return None
        
    def suggested_exe_browse_directory(self) -> str:
        """Return the best starting folder for locating Vectorworks.exe."""
        if not self._known_paths:
            self.find_vectorworks_installations()

        if self._known_paths:
            latest_version = max(self._known_paths.keys())
            return os.path.dirname(self._known_paths[latest_version])

        program_files = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ]
        for program_dir in program_files:
            for relative in ("Vectorworks", os.path.join("Nemetschek", "Vectorworks")):
                candidate = os.path.join(program_dir, relative)
                if os.path.isdir(candidate):
                    return candidate
        return program_files[0]
        
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get the currently active Vectorworks window."""
        foreground_hwnd = win32gui.GetForegroundWindow()
        for window in self.vectorworks_windows:
            window.is_active = window.hwnd == foreground_hwnd
            if window.is_active:
                return window
        return None

    def get_foreground_file(self) -> Optional[str]:
        """Return the file path for the active Vectorworks window, if any."""
        active = self.get_active_window()
        if active and active.file_path:
            return active.file_path
        return None

    def is_render_grace_window(self, title: Optional[str] = None) -> bool:
        """
        Detect transient rendering/export windows that should not end tracking.

        When title is omitted, evaluates the currently active Vectorworks window.
        """
        probe = title
        if probe is None:
            active = self.get_active_window()
            probe = active.title if active else ""
        lowered = (probe or "").lower()
        return any(token in lowered for token in self._render_grace_tokens)

    def get_closed_files(self, clear: bool = True) -> List[str]:
        """Return files closed since the previous refresh."""
        closed = list(self._closed_files)
        if clear:
            self._closed_files.clear()
        return closed
        
    def set_vectorworks_path(self, exe_path: str):
        """Set the path to the Vectorworks executable."""
        if not os.path.exists(exe_path):
            raise FileNotFoundError(f"Vectorworks executable not found at: {exe_path}")
            
        self.vectorworks_path = exe_path
        self.process_name = os.path.basename(exe_path).lower()
        logger.info(f"Set Vectorworks path to: {exe_path}")
        logger.info(f"Monitoring process: {self.process_name}")
        
    def _window_enum_callback(self, hwnd: int, windows: List[WindowInfo]) -> None:
        """Callback for EnumWindows to find Vectorworks windows."""
        if not self.process_name or not self._is_valid_hwnd(hwnd):
            return

        try:
            if not win32gui.IsWindowVisible(hwnd):
                return

            _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(process_id)
            process_name = process.name().lower()

            if process_name != self.process_name:
                return

            title = win32gui.GetWindowText(hwnd)
            if not title:
                return

            file_path = self._get_file_path_from_title(title)
            if not file_path:
                return

            is_visible = self._is_window_visible(hwnd)
            if not any(w.file_path == file_path for w in windows):
                logger.info(f">>> New Vectorworks file detected: {file_path} <<<")
            window_info = WindowInfo(
                hwnd=hwnd,
                title=title,
                process_id=process_id,
                file_path=file_path,
                is_visible=is_visible,
                monitor=None,
            )
            windows.append(window_info)
            logger.debug(f"Vectorworks window: {file_path} (visible={is_visible})")

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.debug(f"Process access error: {e}")
        except Exception as e:
            logger.debug(f"Window enum skipped for hwnd {hwnd}: {e}")
            
    def _get_file_path_from_title(self, title: str) -> Optional[str]:
        """Extract file path from window title if possible."""
        if title.endswith(".vwx"):
            if " - " not in title and "[" not in title:
                return title

        if " - " in title:
            parts = title.split(" - ")
            for part in reversed(parts):
                if part.endswith(".vwx"):
                    return part.strip()

        if "[" in title and "]" in title:
            start = title.find("[") + 1
            end = title.find("]")
            if start > 0 and end > start:
                file_path = title[start:end]
                if file_path.endswith(".vwx"):
                    return file_path

        if ".vwx" in title:
            vwx_index = title.rfind(".vwx")
            if vwx_index != -1:
                start_index = max(
                    title.rfind(" ", 0, vwx_index),
                    title.rfind("-", 0, vwx_index),
                    title.rfind("[", 0, vwx_index),
                    title.rfind("\\", 0, vwx_index),
                )
                if start_index != -1:
                    file_path = title[start_index + 1 : vwx_index + 4].strip()
                    if file_path:
                        return file_path
                file_path = title[: vwx_index + 4].strip()
                if file_path:
                    return file_path

        return None
        
    def _is_window_visible(self, hwnd: int) -> bool:
        """Check if window is visible and not minimized."""
        if not self._is_valid_hwnd(hwnd) or not win32gui.IsWindowVisible(hwnd):
            return False

        try:
            placement = win32gui.GetWindowPlacement(hwnd)
            return placement[1] != win32con.SW_SHOWMINIMIZED
        except Exception as e:
            logger.debug(f"Error checking window visibility for {hwnd}: {e}")
            return False
        
    def refresh(self) -> List[WindowInfo]:
        """Refresh the list of Vectorworks windows."""
        if not self.process_name:
            logger.warning("No Vectorworks executable path set")
            return []

        previous_files = {w.file_path for w in self.vectorworks_windows if w.file_path}
        discovered: List[WindowInfo] = []
        try:
            win32gui.EnumWindows(self._window_enum_callback, discovered)
            foreground_hwnd = win32gui.GetForegroundWindow()
            for window in discovered:
                window.is_active = window.hwnd == foreground_hwnd
        except Exception as e:
            logger.error(f"Vectorworks window refresh failed: {e}")
            return self.vectorworks_windows

        self.vectorworks_windows = discovered
        current_files = {w.file_path for w in self.vectorworks_windows if w.file_path}
        closed = sorted(path for path in (previous_files - current_files) if path)
        if closed:
            self._closed_files.extend(closed)
            for file_path in closed:
                logger.info(f"Detected closed Vectorworks file: {file_path}")
        self._last_file_paths = current_files

        if self.vectorworks_windows:
            logger.debug(f"Found {len(self.vectorworks_windows)} Vectorworks windows")
        else:
            logger.debug("No Vectorworks windows found")

        return self.vectorworks_windows
        
    def is_file_active(self, file_path: str) -> bool:
        """Check if a specific Vectorworks file is currently open and visible."""
        self.refresh()
        for window in self.vectorworks_windows:
            if window.file_path == file_path and window.is_visible:
                return True
        return False 